import streamlit as st
from ebooklib import epub
import ebooklib
from bs4 import BeautifulSoup
import textwrap
import re
import io
import zipfile

# --- 1. ページ設定 ---
st.set_page_config(page_title="EPUB to TXT Converter Online", page_icon="📚")

# --- 2. 変換ロジック (Web用にメモリ内で処理するよう調整) ---
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

# --- 3. UIレイアウト ---
st.title("📚 EPUB to TXT Converter Pro (Web)")
st.write("ファイルをアップロードして、自分好みのテキストに変換しましょう。")

# サイドバー: オプション設定
with st.sidebar:
    st.header("⚙️ 設定")
    var_ruby = st.checkbox("ルビを削除する", value=True)
    var_newline = st.checkbox("元の改行をすべて削除")
    var_images = st.checkbox("画像を抽出する", value=False)
    
    st.divider()
    
    var_blank_mode = st.radio(
        "空行の整理",
        ["そのまま", "1行に統合", "完全に詰める"],
        index=0
    )
    
    st.divider()
    
    use_wrap = st.toggle("指定文字数で改行")
    var_width = st.number_input("文字数", min_value=1, max_value=200, value=40) if use_wrap else 0

# メインエリア: ファイルアップロード
uploaded_files = st.file_uploader("EPUBファイルを選択（複数可）", type="epub", accept_multiple_files=True)

if uploaded_files:
    if st.button("変換を実行する", type="primary", use_container_width=True):
        # 複数のファイルをZIPにまとめるための準備
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
                
                txt, imgs = convert_epub_logic(file, options)
                
                if txt:
                    # テキストファイルをZIPに追加
                    base_name = file.name.replace(".epub", "")
                    zip_file.writestr(f"{base_name}.txt", txt)
                    
                    # 画像があればフォルダを作って追加
                    if imgs:
                        for img_name, img_data in imgs:
                            zip_file.writestr(f"{base_name}_images/{img_name}", img_data)
                
                progress_bar.progress((i + 1) / len(uploaded_files))
            
        st.success("変換が完了しました！")
        
        # ダウンロードボタン
        st.download_button(
            label="📦 変換したファイルをダウンロード (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="converted_files.zip",
            mime="application/zip",
            use_container_width=True
        )