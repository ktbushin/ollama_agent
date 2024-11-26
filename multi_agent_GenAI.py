from ollama import Client
import json
import time
import math

# Ollamaサーバの設定
OLLAMA_HOST = "http://192.168.11.27:11434"
ANALYST_MODEL = "phi3"
PLANNER_MODEL = "phi3"
COMMANDER_MODEL = "phi3"

# ユーザ要求
INSTRUCTION = "Move 10cm forward avoid objects."

# Ollama クライアントの初期化
client = Client(host=OLLAMA_HOST)

# ファイルパス
SENSOR_FILE = "config/sensor_data.json"
ANALYSIS_FILE = "config/analysis.json"
CONTROL_FILE = "config/commands.json"

# Ollamaを利用したチャット関数（モデル指定可能）
def ollama_chat(role, model, content):
    start_time = time.time()

    response = client.chat(model=model, messages=[{"role": "user", "content": content}])
    end_time = time.time()

    print(f"[{role} - {model}] 処理時間: {end_time - start_time:.3f}[sec]")
    return response["message"]["content"]

# センサ値を読み込む
def read_sensor_data(file_path):
    with open(file_path, "r") as file:
        return json.load(file)

# センサ値を整形
def format_ranges(sensor_data):
    """
    ranges の値を整形して 0°, 1°, ... の形式で返す関数。
    
    Args:
        data (list): `ranges` を含む辞書のリスト。
    
    Returns:
        list: 整形された文字列のリスト。
    """
    # 値を取り出して整形
    ranges = sensor_data[0]["ranges"]
    output = []

    for i, value in enumerate(ranges):
        # Infinityを確認して値を文字列として出力
        value_str = "Infinity" if math.isinf(value) else f"{value:.6f}"
        output.append(f"{i}°: {value_str}")

    return output

# JSONデータを書き込む
def write_json_data(file_path, data):
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

# 出力jsonファイルの構文外文字列を削除
def remove_outside_braces(input_string):
    # 最初の { と最後の } の位置を取得
    start = input_string.find('{')
    end = input_string.rfind('}')
    
    # { が存在し、} も存在する場合、そこからその間の文字列を返す
    if start != -1 and end != -1 and start < end:
        return input_string[start:end+1]
    else:
        # { と } が見つからない場合、入力文字列をそのまま返す
        return input_string

# 解析員の処理
def analyst(sensor_data):
    prompt = f"""
    The following is sensor data from a robot's LiDAR (unit: meters): 
    The data consists of 360 distance measurements, one for each degree around the robot (0 to 359 degrees).
    The data starts from the robot's front (0 degrees), and the measurements are in a clockwise direction.
    A value of 'Infinity' means no obstacle is detected in that direction.
    {sensor_data}

    Please analyze this data, detect all obstacles and provide the analysis in **strictly JSON format**. The format should be:

    {{
        "situation": "<Describe the situation, e.g., '6 Obstacle detected'>",
        "obstacles": [
            {{"angle": xxx, "distance": xxx}},
            {{"angle": xxx, "distance": xxx}},
            ...
        ]
    }}

    Only respond the JSON object, no code or explanations.
    """
    # print(prompt)
    reply = ollama_chat("analyst", ANALYST_MODEL, prompt)
    analysis_content = remove_outside_braces(reply)
    print(f"解析員のレスポンス内容: {analysis_content}")

    if not analysis_content.strip():
        print("解析員の応答が空です。")
        return {"situation": "No data", "recommendations": []}

    try:
        analysis = json.loads(analysis_content)
        print(f"解析結果: {analysis}")
    except json.JSONDecodeError as e:
        print(f"JSONデコードエラー: {e}")
        analysis = {"situation": "Invalid response", "recommendations": []}
    return analysis


# 経路計画員の処理
def planner(analysis):

    prompt = f"""
    You are the Path Planner. Based on the following analysis:
    {analysis}
    The user's instruction is: {INSTRUCTION}
    Generate movement commands for the robot in JSON format:
    The direction field specifies the direction in which the robot moves. The following values can be set for this field:
    "forward": Specifies that the robot should move forward. In this case, the distance field should specify the distance to move (e.g., "1m").
    "right": Specifies that the robot should rotate to the right. In this case, the angle field should specify the rotation angle (e.g., "50").
    "backward": Specifies that the robot should move backward. In this case, the distance field should specify the distance to move (e.g., "0.07cm").
    "left": Specifies that the robot should rotate to the left. In this case, the angle field should specify the rotation angle (e.g., "30").
    {{
        "commands": [
            {{"direction": "forward", "distance": "1.0m"}},
            {{"direction": "right", "angle": "50"}},
            {{"direction": "backward", "distance": "0.07m"}},
            {{"direction": "left", "angle": "30"}}
        ]
    }}

    Only respond the JSON object, no code or explanations.
    """
    # print(prompt)
    reply = ollama_chat("planner", PLANNER_MODEL, prompt)
    control_content = remove_outside_braces(reply)
    print(f"経路計画員のレスポンス内容: {control_content}")

    try:
        control = json.loads(control_content)
    except json.JSONDecodeError as e:
        print("エラー: 指令がJSON形式ではありません。", e)
        control = {"commands": []}
    return control

# 司令員
def commander(analysis, control):
    prompt = f"""
    You are the Commander. Based on the analysis and path planning results, review both and decide whether to proceed or request a re-run of the analysis or path planning.

    Analysis Result:
    {analysis}
    
    Path Planning Result:
    {control}

    You have the following options:
    1. "Proceed": If the analysis and path planning are correct.
    2. "Re-run analysis": If you want to request a re-run of the analysis.
    3. "Re-run path planning": If you want to request a re-run of the path planning.

    Please provide your decision as a response, in the following format:
    {{
        "decision": "<Proceed | Re-run analysis | Re-run path planning>",
        "reason": "<Explanation for the decision>"
    }}

    Only respond with the JSON object, no code or explanations.
    """

    # 司令員のレスポンスを取得
    # print(prompt)
    reply = ollama_chat("commander", COMMANDER_MODEL, prompt)
    commander_content = remove_outside_braces(reply)
    print(f"司令員のレスポンス内容: {commander_content}")

    if not commander_content.strip():
        print("司令員の応答が空です。")
        return {"decision": "Re-Run analysis", "reason": "No issues detected."}

    try:
        commander_decision = json.loads(commander_content)
    except json.JSONDecodeError as e:
        print(f"JSONデコードエラー: {e}")
        commander_decision = {"decision": "Re-Run analysis", "reason": "Invalid response"}
    
    return commander_decision

# メイン処理
def main():
    # センサ値を読み込み整形
    sensor_data = read_sensor_data(SENSOR_FILE)
    print(f"センサ値を読み込みました: {len(sensor_data[0]['ranges'])} データポイント")
    formatted_sensor_data = format_ranges(sensor_data)

    # 解析員の処理
    analysis = analyst(formatted_sensor_data)
    write_json_data(ANALYSIS_FILE, analysis)
    print(f"解析結果が {ANALYSIS_FILE} に保存されました。")

    # 経路計画員の処理
    control = planner(analysis)
    write_json_data(CONTROL_FILE, control)
    print(f"指令が {CONTROL_FILE} に保存されました。")

    # 司令員の処理
    commander_decision = commander(analysis, control)
    print(f"司令員の決定: {commander_decision}")

    # ループで繰り返し処理
    while True:
        if commander_decision["decision"] == "Proceed":
            print("司令員が進行を承認しました。処理を終了します。")
            break  # ループを抜けて処理を終了
        elif commander_decision["decision"] == "Re-run analysis":
            # 解析と経路計画を再実行
            print("解析を再実行します...")
            # 解析員の処理
            analysis = analyst(formatted_sensor_data)
            write_json_data(ANALYSIS_FILE, analysis)
            print(f"解析結果が {ANALYSIS_FILE} に保存されました。")

            # 経路計画員の処理
            control = planner(analysis)
            write_json_data(CONTROL_FILE, control)
            print(f"指令が {CONTROL_FILE} に保存されました。")            

            # 司令員の処理
            commander_decision = commander(analysis, control)
            print(f"司令員の決定: {commander_decision}")

            continue  # 解析を再実行するためにループを続ける

        elif commander_decision["decision"] == "Re-run path planning" :
            print("経路計画を再実行します...")
            # 経路計画を再実行
            control = planner(analysis)
            write_json_data(CONTROL_FILE, control)
            print(f"指令が {CONTROL_FILE} に保存されました。")            

            # 司令員の処理
            commander_decision = commander(analysis, control)
            print(f"司令員の決定: {commander_decision}")

            continue  # 計画を再実行するためにループを続ける

        else:
            # 司令員の処理
            commander_decision = commander(analysis, control)
            print(f"司令員の決定: {commander_decision}")

            continue  # 計画を再実行するためにループを続ける


if __name__ == "__main__":
    main()
