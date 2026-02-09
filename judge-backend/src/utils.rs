use std::fs;
use std::path::Path;

/// Clean up temporary files and directories
pub fn cleanup_temp_dir(dir: &str) {
    if Path::new(dir).exists() {
        if let Err(e) = fs::remove_dir_all(dir) {
            log::error!("Failed to clean up temporary directory {}: {}", dir, e);
        }
    }
}

/// Calculate memory usage (platform-dependent)
pub fn get_memory_usage() -> Option<u64> {
    #[cfg(target_os = "windows")]
    {
        use std::process::Command;
        
        let output = Command::new("wmic")
            .args(["process", "where", "name='judge-backend.exe'", "get", "WorkingSetSize"])
            .output()
            .ok()?;
        
        let output_str = String::from_utf8_lossy(&output.stdout);
        let lines: Vec<&str> = output_str.lines().collect();
        
        if lines.len() > 1 {
            let memory_str = lines[1].trim();
            memory_str.parse::<u64>().ok()
        } else {
            None
        }
    }
    
    #[cfg(not(target_os = "windows"))]
    {
        // Implement for other platforms if needed
        None
    }
}
