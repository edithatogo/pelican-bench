#![forbid(unsafe_code)]

/// Return a deterministic conjunctive success flag.
pub fn conjunctive_success(gates: &[bool]) -> bool {
    !gates.is_empty() && gates.iter().all(|value| *value)
}

#[cfg(test)]
mod tests {
    use super::conjunctive_success;
    #[test]
    fn requires_all_gates() {
        assert!(conjunctive_success(&[true, true]));
        assert!(!conjunctive_success(&[true, false]));
        assert!(!conjunctive_success(&[]));
    }
}
