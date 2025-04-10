import json
import ijson
import gzip
import pickle
import os

# === 配置部分 ===
json_file = 'data/onlineBoutique/1744096704422467/trace_results.json'   # 原始 JSON 文件
output_prefix = 'data_batch_'  # 保存文件前缀
batch_size = 10000             # 每多少条数据保存为一个 pkl.gz
output_dir = 'data/onlineBoutique/1744096704422467/batches'         # 保存目录（可以为空）
start_tag = 'item'             # 适用于 [ {...}, {...} ] 的结构

# === 创建保存目录（如不存在） ===
os.makedirs(output_dir, exist_ok=True)

# === 统计已有的批次文件数量，判断从哪条数据开始处理 ===
existing_batches = len([
    f for f in os.listdir(output_dir)
    if f.startswith(output_prefix) and f.endswith('.pkl.gz')
])
start_index = existing_batches * batch_size

print(f"📂 检测到已有 {existing_batches} 个批次文件，将从第 {start_index} 条数据开始续传...")

# === 主逻辑：流式读取 + 跳过 + 分批保存 ===
batch = []
batch_index = existing_batches
current_index = 0

with open(json_file, 'r', encoding='utf-8') as f:
    parser = ijson.items(f, start_tag)

    for item in parser:
        if current_index < start_index:
            current_index += 1
            continue  # 跳过已保存部分

        batch.append(item)
        current_index += 1

        if len(batch) >= batch_size:
            filename = os.path.join(output_dir, f'{output_prefix}{batch_index}.pkl.gz')
            with gzip.open(filename, 'wb') as out:
                pickle.dump(batch, out)

            print(f"✅ 保存批次 {batch_index}（条数：{len(batch)}，总进度：{current_index}）")
            batch = []
            batch_index += 1

    # 最后一批（不足 batch_size 也保存）
    if batch:
        filename = os.path.join(output_dir, f'{output_prefix}{batch_index}.pkl.gz')
        with gzip.open(filename, 'wb') as out:
            pickle.dump(batch, out)

        print(f"✅ 保存最终批次 {batch_index}（条数：{len(batch)}，总进度：{current_index}）")

print("🎉 全部完成！")
