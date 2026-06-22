import os, re

folder = 'src/ui'
for root, _, files in os.walk(folder):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
            # Replace Segoe UI with Terminal
            new_content = re.sub(r'font=\(\"(Segoe UI|Consolas|Arial)\"', 'font=(\"Terminal\"', content)
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                print(f'Updated {path}')

path = 'main.py'
with open(path, 'r', encoding='utf-8') as file:
    content = file.read()
new_content = re.sub(r'font=\(\"(Segoe UI|Consolas|Arial)\"', 'font=(\"Terminal\"', content)
if new_content != content:
    with open(path, 'w', encoding='utf-8') as file:
        file.write(new_content)
    print(f'Updated {path}')
