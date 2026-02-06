# CustomTkinter GUI Design Guide

モダンなPython GUIを作成するためのCustomTkinterガイド。

## インストール

```bash
pip install customtkinter
```

## 基本構造

```python
import customtkinter as ctk

# テーマ設定
ctk.set_appearance_mode("dark")  # "dark", "light", "system"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("アプリ名")
        self.geometry("800x600")
        # ウィジェットをここに追加

app = App()
app.mainloop()
```

---

## ウィジェット一覧

### CTkLabel（ラベル）
```python
label = ctk.CTkLabel(
    master,
    text="テキスト",
    font=ctk.CTkFont(size=16, weight="bold"),
    text_color="white"
)
label.pack(pady=10)
```

### CTkButton（ボタン）
```python
button = ctk.CTkButton(
    master,
    text="クリック",
    command=callback_function,
    width=200,
    height=40,
    corner_radius=10,
    fg_color="#1f6aa5",
    hover_color="#144870"
)
button.pack(pady=10)
```

### CTkEntry（テキスト入力）
```python
entry = ctk.CTkEntry(
    master,
    placeholder_text="入力してください",
    width=300,
    height=35,
    show="*"  # パスワード用
)
entry.pack(pady=10)

# 値取得
value = entry.get()
```

### CTkTextbox（複数行テキスト）
```python
textbox = ctk.CTkTextbox(
    master,
    height=200,
    wrap="word"
)
textbox.pack(fill="x", padx=10, pady=10)

# 値取得
text = textbox.get("1.0", "end-1c")

# 値設定
textbox.insert("1.0", "初期テキスト")
```

### CTkComboBox（ドロップダウン）
```python
combo = ctk.CTkComboBox(
    master,
    values=["選択肢1", "選択肢2", "選択肢3"],
    width=200,
    command=on_select
)
combo.pack(pady=10)
combo.set("選択肢1")  # 初期値

# 値取得
value = combo.get()
```

### CTkSlider（スライダー）
```python
slider = ctk.CTkSlider(
    master,
    from_=0,
    to=100,
    number_of_steps=100,
    command=on_slide
)
slider.pack(pady=10)
slider.set(50)  # 初期値

# 値取得
value = slider.get()
```

### CTkProgressBar（プログレスバー）
```python
progress = ctk.CTkProgressBar(master, width=300)
progress.pack(pady=10)
progress.set(0)  # 0.0 ~ 1.0

# 更新
progress.set(0.5)  # 50%
```

### CTkCheckBox（チェックボックス）
```python
checkbox = ctk.CTkCheckBox(
    master,
    text="オプション",
    command=on_check
)
checkbox.pack(pady=10)

# 状態取得
is_checked = checkbox.get()  # 1 or 0
```

### CTkSwitch（スイッチ）
```python
switch = ctk.CTkSwitch(
    master,
    text="有効/無効",
    command=on_toggle
)
switch.pack(pady=10)

# 状態取得
is_on = switch.get()  # 1 or 0
```

---

## レイアウト

### CTkFrame（フレーム）
```python
frame = ctk.CTkFrame(
    master,
    corner_radius=10,
    fg_color="#2b2b2b"
)
frame.pack(fill="x", padx=20, pady=10)
```

### Pack（パック配置）
```python
widget.pack(
    side="top",      # "top", "bottom", "left", "right"
    fill="x",        # "x", "y", "both", "none"
    expand=True,     # True/False
    padx=10,         # 横の余白
    pady=10,         # 縦の余白
    anchor="w"       # "n", "s", "e", "w", "center"
)
```

### Grid（グリッド配置）
```python
widget.grid(
    row=0,
    column=0,
    rowspan=1,
    columnspan=2,
    sticky="nsew",   # "n", "s", "e", "w" の組み合わせ
    padx=10,
    pady=10
)

# 列/行の重み設定（リサイズ対応）
master.grid_columnconfigure(0, weight=1)
master.grid_rowconfigure(0, weight=1)
```

---

## スタイリング

### フォント
```python
font = ctk.CTkFont(
    family="Meiryo",
    size=14,
    weight="bold"  # "normal", "bold"
)
```

### カラー
```python
# 単色
fg_color="#1f6aa5"

# ダーク/ライトモード対応（タプル）
fg_color=("#dbdbdb", "#333333")  # (light, dark)
```

### よく使う色
```python
# ダークテーマ用
DARK_BG = "#1a1a1a"
DARK_FRAME = "#2b2b2b"
DARK_HOVER = "#3d3d3d"
ACCENT_BLUE = "#1f6aa5"
ACCENT_GREEN = "#2fa572"
TEXT_WHITE = "#ffffff"
TEXT_GRAY = "#a0a0a0"
```

---

## スレッド処理（重い処理用）

```python
import threading

def start_task():
    thread = threading.Thread(target=heavy_task)
    thread.start()

def heavy_task():
    # 重い処理
    result = do_something()

    # UIの更新は after() を使用
    app.after(0, lambda: update_ui(result))

def update_ui(result):
    label.configure(text=result)
```

---

## 完全なサンプル

```python
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("サンプルアプリ")
        self.geometry("500x400")

        # タイトル
        self.title_label = ctk.CTkLabel(
            self,
            text="🎨 サンプルアプリ",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=20)

        # 入力フレーム
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(fill="x", padx=20, pady=10)

        self.entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="テキストを入力"
        )
        self.entry.pack(padx=15, pady=15, fill="x")

        # ボタン
        self.button = ctk.CTkButton(
            self,
            text="実行",
            command=self.on_click
        )
        self.button.pack(pady=10)

        # 結果表示
        self.result_label = ctk.CTkLabel(self, text="")
        self.result_label.pack(pady=10)

    def on_click(self):
        text = self.entry.get()
        self.result_label.configure(text=f"入力: {text}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
```

---

## Sources

- [CustomTkinter Official Documentation](https://customtkinter.tomschimansky.com/)
- [CustomTkinter GitHub](https://github.com/TomSchimansky/CustomTkinter)
- [CustomTkinter Tutorial - DEV Community](https://dev.to/devasservice/customtkinter-a-complete-tutorial-4527)
