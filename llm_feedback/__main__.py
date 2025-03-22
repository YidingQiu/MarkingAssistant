from .generate_feedback_cli import main

if __name__ == "__main__":
    main() 
    
# python -m llm_feedback "rubric\test_results\(Vinnie) Viriya VIRIYAVEJAKUL_z5643139_Lab1_results.json" --model exaone --output-dir feedback --format markdown  

"""
# Generate HTML feedback for a student submission
python -m llm_feedback "rubric\test_results\(Yiding Qiu_z1234567_Lab1_results.json" --model llama3.1 --output-dir feedback --format html

# Generate markdown feedback for a student with spaces in name
python -m llm_feedback "rubric\test_results\Aarav Patel_z5685988_Lab1_results.json" --model llama3.1 --output-dir feedback --format markdown

# Generate markdown feedback for a student with special characters
python -m llm_feedback "rubric\test_results\(Vinnie) Viriya VIRIYAVEJAKUL_z5643139_Lab1_results.json" --model exaone --output-dir feedback --format markdown

# Generate text feedback (plain text without formatting)
python -m llm_feedback "rubric\test_results\(Yiding Qiu_z1234567_Lab1_results.json" --model llama3.1 --output-dir feedback --format text

Note: 
- Always use quotes around filenames with spaces or special characters
- The output file will be named after the student: {student_name}_{student_id}_Lab{lab_number}_feedback.{format}
- Available models: llama3.1, exaone, qwq (default)
- Available formats: html, markdown, text
"""