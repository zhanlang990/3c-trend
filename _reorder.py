import json
with open('data/categories.json','r',encoding='utf-8') as f:
    data = json.load(f)
cats = data['categories']
order = ['3d-printing','uv-printing','cnc','ai-nas','ai-glasses','ai-pc','ai-phone','ai-learning','safe-box','4k-projector','gaming-peripherals','monitor','smart-watch','gaming-desktop','photography','surveillance','speaker','magnetic-accessories','foldable-phone']
by_id = {c['id']:c for c in cats}
data['categories'] = [by_id[i] for i in order]
with open('data/categories.json','w',encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('Done:', [c['id'] for c in data['categories']])