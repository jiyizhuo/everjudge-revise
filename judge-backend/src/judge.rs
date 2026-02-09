use std::sync::Arc;
use std::sync::Mutex;
use std::sync::mpsc;
use std::collections::HashMap;
use std::thread;
use std::time::{SystemTime, Duration};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::fmt;

use crate::languages::LanguageHandler;
use crate::types::{JudgeTask, JudgeStatus};

// 简单的唯一ID生成函数，只使用时间戳
fn generate_unique_id() -> String {
    let timestamp = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .unwrap()
        .as_millis();
    
    format!("{:x}", timestamp)
}

// 任务队列项
struct QueueItem {
    task: JudgeTask,
    task_id: String,
    response_sender: mpsc::Sender<JudgeStatus>,
}

// 线程池
#[derive(Debug)]
struct ThreadPool {
    workers: Vec<thread::JoinHandle<()>>,
    sender: mpsc::Sender<QueueItem>,
    shutdown: Arc<AtomicBool>,
    active_tasks: Arc<AtomicUsize>,
}

impl ThreadPool {
    fn new(size: usize, language_handler: LanguageHandler) -> Self {
        let (sender, receiver) = mpsc::channel::<QueueItem>();
        let shutdown = Arc::new(AtomicBool::new(false));
        let active_tasks = Arc::new(AtomicUsize::new(0));
        let receiver = Arc::new(Mutex::new(receiver));
        
        let mut workers = Vec::with_capacity(size);
        
        for i in 0..size {
            let receiver = receiver.clone();
            let language_handler = language_handler.clone();
            let shutdown = shutdown.clone();
            let active_tasks = active_tasks.clone();
            
            let handle = thread::spawn(move || {
                println!("Worker {} started", i);
                
                loop {
                    // 检查是否应该关闭
                    if shutdown.load(Ordering::Relaxed) {
                        println!("Worker {} shutting down", i);
                        break;
                    }
                    
                    // 从队列中获取任务
                    let item = {
                        let receiver = receiver.lock().unwrap();
                        receiver.recv_timeout(Duration::from_millis(100))
                    };
                    
                    match item {
                        Ok(queue_item) => {
                            // 增加活跃任务计数
                            active_tasks.fetch_add(1, Ordering::Relaxed);
                            
                            println!("Worker {} processing task {}", i, queue_item.task_id);
                            
                            // 执行评测任务
                            let result = language_handler.judge_task(queue_item.task);
                            
                            // 发送结果
                            let _ = queue_item.response_sender.send(result);
                            
                            // 减少活跃任务计数
                            active_tasks.fetch_sub(1, Ordering::Relaxed);
                            
                            println!("Worker {} completed task {}", i, queue_item.task_id);
                        }
                        Err(mpsc::RecvTimeoutError::Timeout) => {
                            // 超时，继续循环
                            continue;
                        }
                        Err(mpsc::RecvTimeoutError::Disconnected) => {
                            // 通道关闭，退出循环
                            println!("Worker {} channel disconnected", i);
                            break;
                        }
                    }
                }
            });
            
            workers.push(handle);
        }
        
        Self {
            workers,
            sender,
            shutdown,
            active_tasks,
        }
    }
    
    fn submit(&self, task: JudgeTask, task_id: String, response_sender: mpsc::Sender<JudgeStatus>) -> Result<(), mpsc::SendError<QueueItem>> {
        self.sender.send(QueueItem {
            task,
            task_id,
            response_sender,
        })
    }
    
    fn shutdown(self) {
        // 设置关闭标志
        self.shutdown.store(true, Ordering::Relaxed);
        
        // 等待所有工作线程完成
        for worker in self.workers {
            let _ = worker.join();
        }
        
        println!("All workers shut down");
    }
    
    fn get_active_count(&self) -> usize {
        self.active_tasks.load(Ordering::Relaxed)
    }
}

// 评测池（包含线程池）
#[derive(Debug)]
pub struct JudgePool {
    tasks: Arc<Mutex<HashMap<String, JudgeStatus>>>,
    thread_pool: Option<ThreadPool>,
    language_handler: LanguageHandler,
    max_threads: usize,
}

impl JudgePool {
    pub fn new(max_threads: usize) -> Result<Self, Box<dyn std::error::Error>> {
        let language_handler = LanguageHandler::new()?;
        let thread_pool = ThreadPool::new(max_threads, language_handler.clone());
        
        Ok(Self {
            tasks: Arc::new(Mutex::new(HashMap::new())),
            thread_pool: Some(thread_pool),
            language_handler,
            max_threads,
        })
    }
    
    pub fn submit_task(
        &mut self,
        submission_id: i32,
        problem_id: i32,
        code: String,
        language: String,
        time_limit: i32,
        memory_limit: u64,
    ) -> String {
        // 生成唯一任务ID
        let task_id = generate_unique_id();
        
        // 初始化任务状态
        {
            let mut tasks = self.tasks.lock().unwrap();
            tasks.insert(
                task_id.clone(),
                JudgeStatus {
                    status: "PENDING".to_string(),
                    score: 0,
                    execution_time: None,
                    memory_used: None,
                    error_message: None,
                }
            );
        }
        
        // 创建响应通道
        let (response_sender, response_receiver) = mpsc::channel::<JudgeStatus>();
        
        // 创建评测任务
        let task = JudgeTask {
            id: task_id.clone(),
            submission_id,
            problem_id,
            code,
            language,
            time_limit,
            memory_limit,
        };
        
        // 提交任务到线程池
        if let Some(ref thread_pool) = self.thread_pool {
            if let Err(e) = thread_pool.submit(task, task_id.clone(), response_sender) {
                println!("Failed to submit task to thread pool: {}", e);
                
                // 更新任务状态为错误
                let mut tasks = self.tasks.lock().unwrap();
                tasks.insert(
                    task_id.clone(),
                    JudgeStatus {
                        status: "SYSTEM_ERROR".to_string(),
                        score: 0,
                        execution_time: None,
                        memory_used: None,
                        error_message: Some(format!("Failed to submit task: {}", e)),
                    }
                );
                
                return task_id;
            }
        }
        
        // 启动一个线程来接收结果并更新任务状态
        let tasks_ref = self.tasks.clone();
        let task_id_clone = task_id.clone();
        
        thread::spawn(move || {
            // 等待评测结果
            match response_receiver.recv() {
                Ok(result) => {
                    // 更新任务状态
                    let mut tasks = tasks_ref.lock().unwrap();
                    tasks.insert(task_id_clone, result);
                }
                Err(e) => {
                    println!("Failed to receive result for task {}: {}", task_id_clone, e);
                    
                    // 更新任务状态为错误
                    let mut tasks = tasks_ref.lock().unwrap();
                    tasks.insert(
                        task_id_clone,
                        JudgeStatus {
                            status: "SYSTEM_ERROR".to_string(),
                            score: 0,
                            execution_time: None,
                            memory_used: None,
                            error_message: Some(format!("Failed to receive result: {}", e)),
                        }
                    );
                }
            }
        });
        
        println!("Task {} submitted to thread pool", task_id);
        task_id
    }
    
    pub fn get_task_status(&self, task_id: &str) -> Option<JudgeStatus> {
        let tasks = self.tasks.lock().unwrap();
        tasks.get(task_id).cloned()
    }
    
    pub fn get_active_tasks_count(&self) -> usize {
        if let Some(ref thread_pool) = self.thread_pool {
            thread_pool.get_active_count()
        } else {
            0
        }
    }
    
    pub fn shutdown(&mut self) {
        if let Some(thread_pool) = self.thread_pool.take() {
            thread_pool.shutdown();
        }
    }
}
