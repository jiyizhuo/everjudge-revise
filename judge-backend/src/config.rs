use serde::Deserialize;
use std::fs::File;
use std::io::Read;
use std::collections::HashMap;

#[derive(Deserialize, Debug, Clone)]
pub struct Config {
    pub server: ServerConfig,
    pub languages: LanguagesConfig,
}

#[derive(Deserialize, Debug, Clone)]
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
    pub max_threads: usize,
}

#[derive(Deserialize, Debug, Clone)]
pub struct LanguagesConfig {
    pub enabled: bool,
    pub supported: Vec<String>,
    pub temp_dir: String,
    pub test_cases_dir: String,
}

#[derive(Deserialize, Debug, Clone)]
pub struct LanguageConfig {
    pub compile_command: Option<String>,
    pub run_command: String,
    pub file_extension: String,
    pub needs_compilation: bool,
}

pub fn load_config() -> Result<Config, Box<dyn std::error::Error>> {
    let mut file = File::open("judge.toml")?;
    let mut contents = String::new();
    file.read_to_string(&mut contents)?;
    
    let config: Config = toml::from_str(&contents)?;
    Ok(config)
}

pub fn load_language_configs() -> Result<HashMap<String, LanguageConfig>, Box<dyn std::error::Error>> {
    let config = load_config()?;
    
    if !config.languages.enabled {
        return Ok(HashMap::new());
    }
    
    let mut language_configs: HashMap<String, LanguageConfig> = HashMap::new();
    
    // 根据配置文件中支持的语言列表加载配置
    for lang in config.languages.supported.iter() {
        let lang_config = match lang.as_str() {
            "c" => LanguageConfig {
                compile_command: Some("gcc {file} -o output.exe".to_string()),
                run_command: "./output.exe".to_string(),
                file_extension: ".c".to_string(),
                needs_compilation: true,
            },
            "cpp" => LanguageConfig {
                compile_command: Some("g++ {file} -o output.exe".to_string()),
                run_command: "./output.exe".to_string(),
                file_extension: ".cpp".to_string(),
                needs_compilation: true,
            },
            "java" => LanguageConfig {
                compile_command: Some("javac {file}".to_string()),
                run_command: "java Main".to_string(),
                file_extension: ".java".to_string(),
                needs_compilation: true,
            },
            "javascript" => LanguageConfig {
                compile_command: None,
                run_command: "node {file}".to_string(),
                file_extension: ".js".to_string(),
                needs_compilation: false,
            },
            "python_2" => LanguageConfig {
                compile_command: None,
                run_command: "python2 {file}".to_string(),
                file_extension: ".py".to_string(),
                needs_compilation: false,
            },
            "python_3" => LanguageConfig {
                compile_command: None,
                run_command: "python3 {file}".to_string(),
                file_extension: ".py".to_string(),
                needs_compilation: false,
            },
            "pascal" => LanguageConfig {
                compile_command: Some("fpc {file}".to_string()),
                run_command: "./code".to_string(),
                file_extension: ".pas".to_string(),
                needs_compilation: true,
            },
            "common_lisp" => LanguageConfig {
                compile_command: None,
                run_command: "sbcl --script {file}".to_string(),
                file_extension: ".lisp".to_string(),
                needs_compilation: false,
            },
            "plain_text" => LanguageConfig {
                compile_command: None,
                run_command: "cat {file}".to_string(),
                file_extension: ".txt".to_string(),
                needs_compilation: false,
            },
            "brainfuck" => LanguageConfig {
                compile_command: None,
                run_command: "bf {file}".to_string(),
                file_extension: ".bf".to_string(),
                needs_compilation: false,
            },
            "r" => LanguageConfig {
                compile_command: None,
                run_command: "Rscript {file}".to_string(),
                file_extension: ".r".to_string(),
                needs_compilation: false,
            },
            "rust" => LanguageConfig {
                compile_command: Some("rustc {file} -o output.exe".to_string()),
                run_command: "./output.exe".to_string(),
                file_extension: ".rs".to_string(),
                needs_compilation: true,
            },
            "kotlin" => LanguageConfig {
                compile_command: Some("kotlinc {file} -include-runtime -d output.jar".to_string()),
                run_command: "java -jar output.jar".to_string(),
                file_extension: ".kt".to_string(),
                needs_compilation: true,
            },
            _ => continue, // 跳过不支持的语言
        };
        
        language_configs.insert(lang.clone(), lang_config);
    }
    
    Ok(language_configs)
}
