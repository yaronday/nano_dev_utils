import sys
import platform
import subprocess

result = subprocess.run(['coverage', 'report'], capture_output=True, text=True)
full_output = result.stdout + result.stderr

platform_ver = sys.platform
py_ver = platform.python_version()

default_len = 80
decor1 = '=' * 32
h_line1 = f'{decor1} tests coverage {decor1}'
inner_text = f' coverage: platform {platform_ver}, python {py_ver} '
h_line2 = inner_text.center(default_len, '_')

formatted = [h_line1, h_line2]

# Include only the test coverage table
lines = full_output.splitlines()
coverage_lines = []
capturing_data = False

for line in lines:
    if 'Stmts' in line or capturing_data:
        capturing_data = True
        formatted.append(line)
    if 'TOTAL' in line:
        break

content = '```text\n' + '\n'.join(formatted) + '\n```\n'
with open('coverage.md', 'w', encoding='utf-8') as f:
    f.write(content)

print('Coverage report successfully updated in coverage.md!')