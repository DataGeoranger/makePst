"""Toy model for the tutorial: reads model.in (written from model.tpl), writes heads.out and flow.out."""
p = {}
for line in open('model.in'):
    name, value = line.split()
    p[name] = float(value)
heads = [100 + 0.1 * p['hk1'] + 500 * p['rch'], 97 + 0.05 * p['hk2'] + 500 * p['rch'], 94 + 0.08 * p['hk3']]
with open('heads.out', 'w') as f:
    f.write('model heads\n')
    for i, h in enumerate(heads, 1):
        f.write(f'well h_w{i}  {h:.3f}\n')
with open('flow.out', 'w') as f:
    f.write(f"flow at gauge {1000 * p['rch'] * (p['hk1'] + p['hk2']) / 30 + 1000:.2f}\n")
