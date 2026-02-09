mod config;
mod server;
mod judge;
mod languages;
mod types;

use std::sync::Arc;
use std::sync::Mutex;
use std::panic;

fn main() {
    // Set up panic hook for better error logging
    panic::set_hook(Box::new(|panic_info| {
        println!("Panic occurred: {:?}", panic_info);
    }));
    
    println!("Initializing judge backend...");
    
    // 从TOML配置文件加载配置
    let config = match config::load_config() {
        Ok(cfg) => cfg,
        Err(e) => {
            println!("Failed to load config: {}", e);
            return;
        }
    };
    
    let judge_pool = match judge::JudgePool::new(config.server.max_threads) {
        Ok(pool) => Arc::new(Mutex::new(pool)),
        Err(e) => {
            println!("Failed to create judge pool: {}", e);
            return;
        }
    };
    
    println!("Starting judge server on {}:{} with {} worker threads", 
             config.server.host, config.server.port, config.server.max_threads);
    
    if let Err(e) = server::run_server(config, judge_pool) {
        println!("Server failed: {}", e);
    }
}
