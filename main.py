import streamlit as st
from ebooklib import epub
import ebooklib
from bs4 import BeautifulSoup
import textwrap
import re
import io
import zipfile

# --- 1. ページ設定 ---
st.set_page_config(page_title="EPUBをTXTにするやつONLINE", page_icon="📚")

# --- 2. 変換ロジック (変更なし) ---
def convert_epub_logic(uploaded_file, options):
    try:
        # メモリ上のバイナリとして読み込み
        book = epub.read_epub(io.BytesIO(uploaded_file.read()))
        full_text = ""
        images = [] # (filename, bytes) のリスト

        # 文章の処理
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            if options['remove_ruby']:
                for rt in soup.find_all('rt'):
                    rt.decompose()
            text = soup.get_text()
            if options['remove_newlines']:
                text = text.replace('\n', '').replace('\r', '')
            full_text += text + "\n"

        # 空行の処理
        if options['blank_mode'] == "1行に統合":
            full_text = re.sub(r'\n\s*\n+', '\n\n', full_text)
        elif options['blank_mode'] == "完全に詰める":
            full_text = re.sub(r'\n\s*\n+', '\n', full_text)

        # 文字数折り返し
        if options['wrap_width'] > 0:
            lines = full_text.splitlines()
            full_text = "\n".join([textwrap.fill(line, width=options['wrap_width']) for line in lines])

        # 画像の抽出
        if options['save_images']:
            for image in book.get_items_of_type(ebooklib.ITEM_IMAGE):
                images.append((image.get_name(), image.get_content()))

        return full_text, images
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        return None, None

# --- 3. UIレイアウト (ここを大幅に変更) ---
st.title("📚 EPUBをTXTにするやつONLINE")

# ▼▼▼ 追加：余白を詰めるためのCSS ▼▼▼
st.markdown("""
    <style>
    /* ファイルアップローダーの下の余白を削る */
    .stFileUploader {
        margin-bottom: -20px;
    }
    /* 区切り線(hr)の上下余白を削る */
    hr {
        margin-top: 0px !important;
        margin-bottom: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)
# ▲▲▲ 追加ここまで ▲▲▲

st.write("スマホでも簡単に変換できるやつ。")

# 1. ファイルアップロードを一番上に配置
uploaded_files = st.file_uploader("EPUBファイルを選択（複数可）", type="epub", accept_multiple_files=True)

# 2. 変換ボタンをその下に配置
# ここでボタンが押されたかどうかの状態を変数(run_pressed)に保存します
run_pressed = False
if uploaded_files:
    run_pressed = st.button("変換を実行する", type="primary", use_container_width=True)

# 3. 設定エリアをさらに下に配置
st.markdown("---") # 見やすくするための区切り線
# 画面下部なので、デフォルトは閉じておき(expanded=False)、必要な人だけ開く仕様にしました
with st.expander("⚙️ オプション設定（変更する場合はここをタップ）", expanded=True):
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.caption("基本設定")
        var_ruby = st.checkbox("ルビを削除する", value=True)
        var_newline = st.checkbox("元の改行を削除")
        var_images = st.checkbox("画像を抽出する", value=False)

    with col2:
        st.caption("空行設定")
        var_blank_mode = st.radio(
            "空行の扱い",
            ["そのまま", "1行に統合", "詰める"],
            index=0
        )
    
    st.divider()

    # 折り返し設定
    # value=True を追加することで、最初からONになります
    use_wrap = st.toggle("指定文字数で改行", value=True)
    
    if use_wrap:
        var_width = st.slider("文字数", min_value=1, max_value=100, value=20)
    else:
        var_width = 0

# --- 4. 実行処理ブロック (配置はUIの後だが、ボタン判定で動く) ---
if run_pressed and uploaded_files:
    # ここに来た時点で「設定エリア」の変数は読み込まれているので安全に使用できます
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        progress_bar = st.progress(0)
        
        for i, file in enumerate(uploaded_files):
            options = {
                'remove_ruby': var_ruby,
                'remove_newlines': var_newline,
                'blank_mode': var_blank_mode,
                'save_images': var_images,
                'wrap_width': var_width
            }
            
            if options['blank_mode'] == "詰める":
                options['blank_mode'] = "完全に詰める"
            
            txt, imgs = convert_epub_logic(file, options)
            
            if txt:
                base_name = file.name.replace(".epub", "")
                zip_file.writestr(f"{base_name}.txt", txt)
                
                if imgs:
                    for img_name, img_data in imgs:
                        zip_file.writestr(f"{base_name}_images/{img_name}", img_data)
            
            progress_bar.progress((i + 1) / len(uploaded_files))
        
    st.success("変換完了！下のボタンから保存してください。")
    
    st.download_button(
        label="📦 まとめてダウンロード (ZIP)",
        data=zip_buffer.getvalue(),
        file_name="converted_files.zip",
        mime="application/zip",
        use_container_width=True
    )

# --- 5. フッター（署名・免責） ---
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; font-size: 12px; color: #888888; line-height: 1.6;">
        <p style="margin-bottom: 5px;">Created by <strong>ごんざれす</strong></p>
        <p>
            <a href="https://x.com/jyukaiin" target="_blank" style="color: #1DA1F2; text-decoration: none; font-weight: bold;">
                𝕏 @jyukaiin
            </a>
        </p>
        <p style="margin-top: 15px; font-size: 10px;">
            ※免責事項：アップロードされたファイルはサーバーに保存されず、メモリ上で一時的に処理されます。<br>
            本ツールの利用によって生じた損害等について、製作者は一切の責任を負いません。
        </p>
    </div>
    """,
    unsafe_allow_html=True
)


