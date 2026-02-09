#[derive(Debug, Clone)]
pub struct JudgeTask {
    pub id: String,
    pub submission_id: i32,
    pub problem_id: i32,
    pub code: String,
    pub language: String,
    pub time_limit: i32, // milliseconds
    pub memory_limit: u64, // bytes
}

#[derive(Debug, Clone)]
pub struct JudgeStatus {
    pub status: String,
    pub score: i32,
    pub execution_time: Option<i32>,
    pub memory_used: Option<i32>,
    pub error_message: Option<String>,
}
