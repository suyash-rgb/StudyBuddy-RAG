import re
line = 'A[Score (90)]'
line = re.sub(r'\b([a-zA-Z0-9_\-]+)\s*\[\s*([^"\]]+?)\s*\]', r'\1["\2"]', line)
def replace_round(m):
    before = line[:m.start()]
    if before.count('"') % 2 == 1: return m.group(0)
    return f'{m.group(1)}("{m.group(2)}")'
line = re.compile(r'\b([a-zA-Z0-9_\-]+)\s*\(\s*([^"\)]+?)\s*\)').sub(replace_round, line)
print(line)
