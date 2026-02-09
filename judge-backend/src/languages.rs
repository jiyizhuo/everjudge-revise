use std::process::{Command, Stdio};
use std::fs::{File, write};
use std::path::Path;
use std::io::{Write, Read};
use std::time::Duration;
use std::collections::HashMap;

use crate::types::{JudgeTask, JudgeStatus};
use crate::config::{LanguageConfig, load_language_configs};

#[derive(Debug, Clone)]
pub struct LanguageHandler {
    language_configs: HashMap<String, LanguageConfig>,
    test_cases_dir: String,
    temp_dir: String,
}

impl LanguageHandler {
    pub fn new() -> Result<Self, Box<dyn std::error::Error>> {
        // 从TOML配置加载语言配置
        let language_configs = load_language_configs()?;
        
        // 获取配置中的目录路径
        let config = crate::config::load_config()?;
        let test_cases_dir = config.languages.test_cases_dir;
        let temp_dir = config.languages.temp_dir;
        
        Ok(Self {
            language_configs,
            test_cases_dir,
            temp_dir,
        })
    }
    
    pub fn judge_task(&self, task: JudgeTask) -> JudgeStatus {
        // 检查语言是否启用
        let normalized_lang = self.normalize_language_name(&task.language);
        if !self.language_configs.contains_key(&normalized_lang) {
            return JudgeStatus {
                status: "SYSTEM_ERROR".to_string(),
                score: 0,
                execution_time: None,
                memory_used: None,
                error_message: Some(format!("Language '{}' is not enabled or supported", task.language)),
            };
        }
        
        let lang_config = &self.language_configs[&normalized_lang];
        
        // 创建临时目录
        let temp_dir = format!("{}/{}", self.temp_dir, task.id);
        let _ = std::fs::create_dir_all(&temp_dir);
        
        // 写入代码文件
        let code_file = format!("{}/code{}", temp_dir, lang_config.file_extension);
        if let Err(e) = write(&code_file, &task.code) {
            return JudgeStatus {
                status: "SYSTEM_ERROR".to_string(),
                score: 0,
                execution_time: None,
                memory_used: None,
                error_message: Some(format!("Failed to write code file: {}", e)),
            };
        }
        
        // 编译阶段
        if lang_config.needs_compilation {
            if let Some(cmd) = &lang_config.compile_command {
                let compile_result = Command::new("cmd")
                    .args(["/c", &cmd.replace("{file}", &code_file)])
                    .current_dir(&temp_dir)
                    .output()
                    .expect("Failed to execute compile command");
                
                if !compile_result.status.success() {
                    let error_message = String::from_utf8_lossy(&compile_result.stderr).to_string();
                    return JudgeStatus {
                        status: "COMPILATION_ERROR".to_string(),
                        score: 0,
                        execution_time: None,
                        memory_used: None,
                        error_message: Some(error_message),
                    };
                }
            }
        }
        
        // 加载测试用例
        let test_cases = self.load_test_cases(task.problem_id);
        
        if test_cases.is_empty() {
            // 没有测试用例，返回ACCEPTED
            return JudgeStatus {
                status: "ACCEPTED".to_string(),
                score: 100,
                execution_time: Some(0),
                memory_used: None,
                error_message: None,
            };
        }
        
        // 评估测试用例
        let mut passed_tests = 0;
        let mut total_time = 0;
        
        for (i, (input, expected_output)) in test_cases.iter().enumerate() {
            // 创建输入文件
            let input_file = format!("{}/input{}.txt", temp_dir, i);
            if let Err(e) = write(&input_file, input) {
                return JudgeStatus {
                    status: "SYSTEM_ERROR".to_string(),
                    score: 0,
                    execution_time: None,
                    memory_used: None,
                    error_message: Some(format!("Failed to write input file: {}", e)),
                };
            }
            
            // 执行阶段
            let run_command = lang_config.run_command.replace("{file}", &code_file);
            let start_time = std::time::Instant::now();
            
            let output = Command::new("cmd")
                .args(["/c", &format!("{}", run_command)])
                .current_dir(&temp_dir)
                .stdin(Stdio::from(File::open(&input_file).unwrap()))
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .output()
                .expect("Failed to execute run command");
            
            let execution_time = start_time.elapsed().as_millis() as i32;
            total_time += execution_time;
            
            // 检查时间限制
            if execution_time > task.time_limit {
                return JudgeStatus {
                    status: "TIME_LIMIT_EXCEEDED".to_string(),
                    score: 0,
                    execution_time: Some(execution_time),
                    memory_used: None,
                    error_message: Some(format!("Time limit exceeded: {}ms > {}ms", execution_time, task.time_limit)),
                };
            }
            
            // 检查程序是否成功退出
            if !output.status.success() {
                let error_message = String::from_utf8_lossy(&output.stderr).to_string();
                return JudgeStatus {
                    status: "RUNTIME_ERROR".to_string(),
                    score: 0,
                    execution_time: Some(execution_time),
                    memory_used: None,
                    error_message: Some(error_message),
                };
            }
            
            // 比较输出
            let actual_output = String::from_utf8_lossy(&output.stdout).to_string();
            if self.compare_outputs(&actual_output, expected_output) {
                passed_tests += 1;
            }
        }
        
        // 计算得分
        let score = (passed_tests * 100) / test_cases.len();
        let status = if score == 100 {
            "ACCEPTED"
        } else if score > 0 {
            "PARTIALLY_CORRECT"
        } else {
            "WRONG_ANSWER"
        };
        
        JudgeStatus {
            status: status.to_string(),
            score: score as i32,
            execution_time: Some(total_time / test_cases.len() as i32),
            memory_used: None,
            error_message: None,
        }
    }
    
    fn load_test_cases(&self, problem_id: i32) -> Vec<(String, String)> {
        // 从配置的测试用例目录加载测试用例
        let problem_dir = format!("{}/{}", self.test_cases_dir, problem_id);
        let test_cases_dir = Path::new(&problem_dir);
        
        if !test_cases_dir.exists() {
            // 如果测试用例目录不存在，返回默认的测试用例
            return vec![
                ("5\n10\n".to_string(), "15\n".to_string()),
                ("3\n7\n".to_string(), "10\n".to_string()),
            ];
        }
        
        // 读取测试用例目录中的所有输入输出文件
        let mut test_cases = Vec::new();
        let entries = std::fs::read_dir(&problem_dir);
        
        if let Ok(entries) = entries {
            let mut input_files: Vec<_> = entries
                .filter_map(|e| e.ok())
                .filter(|e| e.path().extension().map_or(false, |ext| ext == "in"))
                .collect();
            
            input_files.sort_by_key(|a| a.path());
            
            for input_file in input_files {
                let input_path = input_file.path();
                let output_path = input_path.with_extension("out");
                
                let input_content = File::open(&input_path)
                    .and_then(|mut f| {
                        let mut content = String::new();
                        f.read_to_string(&mut content)?;
                        Ok(content)
                    })
                    .unwrap_or_default();
                
                let expected_output = File::open(&output_path)
                    .and_then(|mut f| {
                        let mut content = String::new();
                        f.read_to_string(&mut content)?;
                        Ok(content)
                    })
                    .unwrap_or_default();
                
                test_cases.push((input_content, expected_output));
            }
        }
        
        test_cases
    }
    
    fn compare_outputs(&self, actual: &str, expected: &str) -> bool {
        // 标准化输出，去除空白和换行
        let actual_normalized = actual.trim().replace("\r\n", "\n").replace("\r", "\n");
        let expected_normalized = expected.trim().replace("\r\n", "\n").replace("\r", "\n");
        
        actual_normalized == expected_normalized
    }
    
    fn normalize_language_name(&self, language: &str) -> String {
        // 标准化语言名称，用于配置查找
        language.to_lowercase()
            .replace(" ", "_")
            .replace("+", "p")
            .replace(".", "")
            .replace("c++", "cpp")
            .replace("node.js", "javascript")
            .replace("python 2", "python_2")
            .replace("python 3", "python_3")
            .replace("common lisp", "common_lisp")
            .replace("plain text", "plain_text")
            .replace("brainfuck", "brainfuck")
    }
}
