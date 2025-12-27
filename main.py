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

# --- 2. 変換ロジック ---
def convert_epub_logic(uploaded_file, options):
    try:
        uploaded_file.seek(0)
        book = epub.read_epub(io.BytesIO(uploaded_file.read()))
        full_text = ""
        images = [] 

        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            
            # ルビ削除
            if options['remove_ruby']:
                for rt in soup.find_all('rt'):
                    rt.decompose()
            
            text = soup.get_text()
            full_text += text + "\n"

        # --- 改行・空行の統合処理 ---
        if options['line_mode'] == "改行を全削除":
            # すべての改行・空白を一度消去（テキストのリセット）
            full_text = re.sub(r'[\n\r\s]+', '', full_text)
        elif options['line_mode'] == "空行を削除":
            # 連続する改行（空行）を1つの改行に集約
            full_text = re.sub(r'\n\s*\n+', '\n', full_text)
        
        # --- 文字数折り返し処理 ---
        # 「全削除」後の再整形、または既存行の折り返し
        if options['wrap_width'] > 0:
            if options['line_mode'] == "改行を全削除":
                # ひと塊になったテキストを指定幅でパッキング
                full_text = textwrap.fill(full_text, width=options['wrap_width'])
            else:
                # 各行の長さを指定幅以内に収める
                lines = full_text.splitlines()
                full_text = "\n".join([textwrap.fill(line, width=options['wrap_width']) for line in lines])

        # 画像の抽出
        if options['save_images']:
            for image in book.get_items_of_type(ebooklib.ITEM_IMAGE):
                images.append((image.get_name(), image.get_content()))

        return full_text, images
    except Exception as e:
        st.error(f"エラーが発生しました({uploaded_file.name}): {e}")
        return None, None

# --- 3. UIレイアウト & スタイル改善 ---
st.markdown("""
    <style>
    html { font-size: 14px; }
    h1 { font-size: 1.8rem !important; margin-bottom: 0.5rem; }
    
    /* ボタンデザイン */
    .stButton > button {
        height: 3.5rem;
        border-radius: 12px;
        font-weight: bold;
        font-size: 1.1rem !important;
        margin-top: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* UIパーツの隙間調整 */
    .stFileUploader { margin-bottom: -10px; }
    [data-testid="stExpander"] { border-radius: 10px; border: 1px solid #ddd; }
    
    /* スライダーやラジオボタンのラベルを見やすく */
    div[data-testid="stMarkdownContainer"] > p { font-size: 1rem; }
    </style>
    """, unsafe_allow_html=True)

st.title("📚 EPUBをTXTにするやつ")
st.write("スマホでEPUBをきれいにTXT化。")

# 1. ファイルアップロード
uploaded_files = st.file_uploader(
    "EPUBファイルを選択", 
    type="epub", 
    accept_multiple_files=True
)

# 2. 変換ボタン
run_pressed = False
if uploaded_files:
    run_pressed = st.button("変換を実行する", type="primary", use_container_width=True)

# 結果表示用コンテナ
result_container = st.container()

# 3. オプション設定
st.markdown("---")
with st.expander("⚙️ オプション設定", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        var_ruby = st.checkbox("ルビを削除する", value=True)
        var_images = st.checkbox("画像を抽出する", value=False)
        
    with col2:
        var_line_mode = st.radio(
            "改行・空行の扱い",
            ["そのまま", "空行を削除", "改行を全削除"],
            index=1,
            help="「全削除」した後に下の文字数指定を使うと、好きな幅で再整列できます。"
        )
    
    st.divider()

    # 折り返し設定（全削除モードでも有効化）
    use_wrap = st.toggle("指定文字数で改行を入れる", value=False)
    var_width = st.slider("1行の文字数", 1, 100, 35, disabled=not use_wrap)
    
    if not use_wrap:
        var_width = 0

# --- 4. 実行処理 ---
if run_pressed and uploaded_files:
    is_single_txt = len(uploaded_files) == 1 and not var_images
    zip_buffer = io.BytesIO()
    single_txt_data = ""
    single_filename = ""
    
    with result_container:
        with st.spinner('変換中...'):
            progress_bar = st.progress(0)
            
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for i, file in enumerate(uploaded_files):
                    options = {
                        'remove_ruby': var_ruby,
                        'line_mode': var_line_mode,
                        'save_images': var_images,
                        'wrap_width': var_width
                    }
                    
                    txt, imgs = convert_epub_logic(file, options)
                    
                    if txt:
                        # 拡張子を除去
                        base_name = re.sub(r'\.epub$', '', file.name, flags=re.IGNORECASE)
                        
                        if is_single_txt:
                            single_txt_data = txt
                            single_filename = f"{base_name}.txt"
                        
                        zip_file.writestr(f"{base_name}.txt", txt)
                        if imgs:
                            for img_name, img_data in imgs:
                                zip_file.writestr(f"{base_name}_images/{img_name}", img_data)
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
            
            st.success("完了しました！")
            
            if is_single_txt:
                st.download_button(
                    label="📄 TXTを保存",
                    data=single_txt_data,
                    file_name=single_filename,
                    mime="text/plain",
                    use_container_width=True
                )
            else:
                st.download_button(
                    label="📦 まとめて保存 (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="converted_files.zip",
                    mime="application/zip",
                    use_container_width=True
                )
        st.markdown("---")

# --- 5. フッター ---
st.markdown(
    """
    <div style="text-align: center; font-size: 11px; color: #888888; margin-top: 50px;">
        <p>Created by <strong>ごんざれす</strong> | <a href="https://x.com/jyukaiin" target="_blank" style="color: #1DA1F2; text-decoration: none;">𝕏 @jyukaiin</a></p>
    </div>
    """,
    unsafe_allow_html=True
)
