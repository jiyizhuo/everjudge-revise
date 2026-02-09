use std::sync::Arc;
use std::sync::Mutex;
use std::net::{TcpListener, TcpStream};
use std::io::{Read, Write};
use std::thread;
use serde::{Deserialize, Serialize};

use crate::judge::JudgePool;
use crate::config::Config;

#[derive(Deserialize, Debug)]
struct Request {
    action: String,
    submission_id: Option<i32>,
    problem_id: Option<i32>,
    code: Option<String>,
    language: Option<String>,
    time_limit: Option<i32>,
    memory_limit: Option<u64>,
    judge_id: Option<String>,
}

#[derive(Serialize, Debug)]
struct Response {
    status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    judge_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    data: Option<JudgeResult>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<String>,
}

#[derive(Serialize, Debug)]
struct JudgeResult {
    status: String,
    score: i32,
    execution_time: Option<i32>,
    memory_used: Option<i32>,
    error_message: Option<String>,
}

pub fn run_server(
    config: Config,
    judge_pool: Arc<Mutex<JudgePool>>,
) -> Result<(), Box<dyn std::error::Error>> {
    let addr = format!("{}:{}", config.server.host, config.server.port);
    let listener = TcpListener::bind(&addr)?;
    
    println!("Server started, listening on {}", addr);
    
    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                let judge_pool_clone = judge_pool.clone();
                thread::spawn(move || {
                    handle_client(stream, judge_pool_clone);
                });
            }
            Err(e) => {
                println!("Failed to accept connection: {}", e);
            }
        }
    }
    
    Ok(())
}

fn handle_client(mut stream: TcpStream, judge_pool: Arc<Mutex<JudgePool>>) {
    let mut buf = [0; 4096];
    
    loop {
        match stream.read(&mut buf) {
            Ok(0) => {
                // Connection closed
                break;
            }
            Ok(n) => {
                let data = &buf[..n];
                let request_str = match std::str::from_utf8(data) {
                    Ok(s) => s,
                    Err(e) => {
                        println!("Failed to parse UTF-8: {}", e);
                        break;
                    }
                };
                
                let request: Request = match serde_json::from_str(request_str) {
                    Ok(req) => req,
                    Err(e) => {
                        println!("Failed to parse JSON: {}", e);
                        let response = Response {
                            status: "error".to_string(),
                            judge_id: None,
                            data: None,
                            error: Some(format!("Invalid JSON: {}", e)),
                        };
                        let response_json = serde_json::to_string(&response).unwrap();
                        let _ = stream.write_all(response_json.as_bytes());
                        break;
                    }
                };
                
                match request.action.as_str() {
                    "submit" => {
                        if let (Some(submission_id), Some(problem_id), Some(code), Some(language), Some(time_limit), Some(memory_limit)) = (
                            request.submission_id, request.problem_id, request.code, request.language, request.time_limit, request.memory_limit
                        ) {
                            let mut judge_pool = judge_pool.lock().unwrap();
                            let judge_id = judge_pool.submit_task(
                                submission_id,
                                problem_id,
                                code,
                                language,
                                time_limit,
                                memory_limit,
                            );
                            
                            let response = Response {
                                status: "ok".to_string(),
                                judge_id: Some(judge_id),
                                data: None,
                                error: None,
                            };
                            let response_json = serde_json::to_string(&response).unwrap();
                            let _ = stream.write_all(response_json.as_bytes());
                        } else {
                            let response = Response {
                                status: "error".to_string(),
                                judge_id: None,
                                data: None,
                                error: Some("Missing required fields for submit action".to_string()),
                            };
                            let response_json = serde_json::to_string(&response).unwrap();
                            let _ = stream.write_all(response_json.as_bytes());
                        }
                    }
                    "status" => {
                        if let Some(judge_id) = request.judge_id {
                            let judge_pool = judge_pool.lock().unwrap();
                            let result = judge_pool.get_task_status(&judge_id);
                            match result {
                                Some(status) => {
                                    let response = Response {
                                        status: "ok".to_string(),
                                        judge_id: None,
                                        data: Some(JudgeResult {
                                            status: status.status,
                                            score: status.score,
                                            execution_time: status.execution_time,
                                            memory_used: status.memory_used,
                                            error_message: status.error_message,
                                        }),
                                        error: None,
                                    };
                                    let response_json = serde_json::to_string(&response).unwrap();
                                    let _ = stream.write_all(response_json.as_bytes());
                                }
                                None => {
                                    let response = Response {
                                        status: "error".to_string(),
                                        judge_id: None,
                                        data: None,
                                        error: Some("Judge ID not found".to_string()),
                                    };
                                    let response_json = serde_json::to_string(&response).unwrap();
                                    let _ = stream.write_all(response_json.as_bytes());
                                }
                            }
                        } else {
                            let response = Response {
                                status: "error".to_string(),
                                judge_id: None,
                                data: None,
                                error: Some("Missing judge_id for status action".to_string()),
                            };
                            let response_json = serde_json::to_string(&response).unwrap();
                            let _ = stream.write_all(response_json.as_bytes());
                        }
                    }
                    "stats" => {
                        let judge_pool = judge_pool.lock().unwrap();
                        let active_count = judge_pool.get_active_tasks_count();
                        
                        let response = Response {
                            status: "ok".to_string(),
                            judge_id: None,
                            data: Some(JudgeResult {
                                status: "RUNNING".to_string(),
                                score: active_count as i32,
                                execution_time: None,
                                memory_used: None,
                                error_message: None,
                            }),
                            error: None,
                        };
                        let response_json = serde_json::to_string(&response).unwrap();
                        let _ = stream.write_all(response_json.as_bytes());
                    }
                    _ => {
                        let response = Response {
                            status: "error".to_string(),
                            judge_id: None,
                            data: None,
                            error: Some(format!("Unknown action: {}", request.action)),
                        };
                        let response_json = serde_json::to_string(&response).unwrap();
                        let _ = stream.write_all(response_json.as_bytes());
                    }
                }
            }
            Err(e) => {
                println!("Failed to read from stream: {}", e);
                break;
            }
        }
    }
}
