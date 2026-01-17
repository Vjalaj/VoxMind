# Contribution.md - Priyapal

## Week 1: Advanced Command Parser

### What I did:
- **Advanced Command Parser**: Created comprehensive `command_parser.py`
  - 40+ command patterns with regex matching
  - Support for 12 command types:
    - open_browser, search, get_time, system_power
    - control_volume, control_app, open_path
    - assistant_help, navigate, media_control, scroll
  - Parameter extraction (browser names, search queries, app names, etc.)
  - Wake word stripping (jarvis, hey jarvis, ok jarvis, hey vox, vox)
  - Fast-fail keyword indexing for performance
  - Synonym support and natural language variations
  - Smart fallback to search for unknown commands

- **Testing**: Created `test_parser.py` with sample test cases

### Resources used:
- Python regex documentation
- Stack Overflow for pattern matching
- ChatGPT for optimization
- Amazon Q for code review

### Challenges faced:
1. **Pattern conflicts**: Multiple patterns matching same input
   - Solution: Ordered patterns by specificity, keyword indexing

2. **Parameter extraction**: Complex regex for extracting values
   - Solution: Named groups and dedicated extractor functions

3. **Performance**: Regex matching on every command
   - Solution: Keyword index for fast-fail optimization


### Next steps (Week 2):
- Improve wake word accuracy
- Reduce false positive rate
- Add sensitivity adjustment
- Support multiple wake words
- Implement local wake word detection (Porcupine)
- Lead QA and testing efforts

---

## Week 2: QA Lead & Wake Word Enhancement

### What I will do:

**Wake Word Enhancements:**
- Reduce false positive rate
- Improve detection in noisy environments
- Add sensitivity adjustment
- Support multiple wake words ("Hey Vox", "Vox")
- Implement local wake word detection (Porcupine optional)

**Quality Assurance (PRIMARY ROLE):**
- Create comprehensive test suite
- Test detection accuracy (true positive rate)
- Test false positive rate
- Test in different noise levels
- Test with different speakers
- Test detection latency
- Test continuous listening stability

**Testing Coordination:**
- Help team members write tests
- Review test coverage
- Create testing guidelines
- Document testing best practices
- Set up test automation

### Timeline:
- **Day 1-2**: Wake word improvements
- **Day 3-4**: QA test suite creation
- **Day 5**: Testing coordination
- **Day 6**: Test automation
- **Day 7**: Documentation

### Success Criteria:
- Wake word accuracy >95%
- False positive rate <5%
- Test coverage >80% across all modules
- Testing guidelines documented

---

## Contact
- Tech Lead: Jalaj
- Questions: Team Whatsapp
- Code Reviews: PR and tag Jalaj
