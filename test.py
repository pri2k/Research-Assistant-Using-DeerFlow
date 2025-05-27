import subprocess

def run_deerflow(query: str) -> str:
    deerflow_main = "/Users/priyakeshri/Desktop/Recent/Intern/newfile/deer-flow/main.py"
    command = ['uv', 'run', deerflow_main, query]
    output_lines = []

    try:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as process:
            for line in process.stdout:
                print(line, end="")  # live output
                output_lines.append(line)

        full_output = ''.join(output_lines)

        # ✅ Extract the final report starting from "reporter response:"
        marker = "reporter response:"
        marker_index = full_output.find(marker)

        if marker_index != -1:
            final_report = full_output[marker_index + len(marker):].strip()
            return final_report
        else:
            return "⚠️ 'reporter response:' not found in output.\n" + full_output.strip()

    except Exception as e:
        return f"❌ Error: {str(e)}"



if __name__ == "__main__":
    user_query = input("Enter your query: ")
    output = run_deerflow(user_query)
    print("\n--- Deerflow Output ---\n")
    print(output)
