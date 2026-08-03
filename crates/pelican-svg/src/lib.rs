#![forbid(unsafe_code)]

/// Preflight markers rejected before XML parsing in the Python reference.
pub const FORBIDDEN_MARKERS: [&str; 3] = ["<!doctype", "<!entity", "<?xml-stylesheet"];

pub fn preflight_safe(source: &str) -> bool {
    let lowered = source.to_ascii_lowercase();
    !FORBIDDEN_MARKERS
        .iter()
        .any(|marker| lowered.contains(marker))
}

#[cfg(test)]
mod tests {
    use super::preflight_safe;
    #[test]
    fn rejects_entity_declarations() {
        assert!(!preflight_safe("<!ENTITY x 'y'><svg/>"));
        assert!(preflight_safe("<svg/>"));
    }
}
