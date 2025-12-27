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
        # メモリ上のバイナリとして読み込み
        # seek(0) は念のため（再読み込み時の保険）
        uploaded_file.seek(0)
        book = epub.read_epub(io.BytesIO(uploaded_file.read()))
        full_text = ""
        images = [] # (filename, bytes) のリスト

        # 文章の処理
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            
            # ルビ削除
            if options['remove_ruby']:
                for rt in soup.find_all('rt'):
                    rt.decompose()
            
            text = soup.get_text()
            
            # 改行削除（文中の改行トル）
            if options['remove_newlines']:
                text = text.replace('\n', '').replace('\r', '')
            
            full_text += text + "\n"

        # 空行の処理（正規表現で空行を整理）
        if options['blank_mode'] == "1行に統合":
            full_text = re.sub(r'\n\s*\n+', '\n\n', full_text)
        elif options['blank_mode'] == "完全に詰める":
            full_text = re.sub(r'\n\s*\n+', '\n', full_text)

        # 文字数折り返し
        if options['wrap_width'] > 0:
            lines = full_text.splitlines()
            # textwrapは日本語の禁則処理を考慮しないが、標準機能としてはこれでOK
            full_text = "\n".join([textwrap.fill(line, width=options['wrap_width']) for line in lines])

        # 画像の抽出
        if options['save_images']:
            for image in book.get_items_of_type(ebooklib.ITEM_IMAGE):
                images.append((image.get_name(), image.get_content()))

        return full_text, images
    except Exception as e:
        # エラー時はNoneを返すのではなくエラー文言を入れる手もあるが、今回はUI側で制御
        st.error(f"エラーが発生しました({uploaded_file.name}): {e}")
        return None, None

# --- 3. UIレイアウト ---
st.title("📚 EPUBをTXTにするやつONLINE")
st.write("スマホでも簡単に変換できるやつ。")

st.markdown("""
    <style>
    .stFileUploader { margin-bottom: -20px; }
    hr { margin-top: 0px !important; margin-bottom: 10px !important; }
    </style>
    """, unsafe_allow_html=True)

# 1. ファイルアップロード
uploaded_files = st.file_uploader(
    "EPUBファイルを選択", 
    type="epub", 
    accept_multiple_files=True,
    help="最大10個まで。複数選択時はZIPで出力されます。"
)

# 2. 変換ボタン
run_pressed = False
if uploaded_files:
    run_pressed = st.button("変換を実行する", type="primary", use_container_width=True)

# 結果表示用コンテナ
result_container = st.container()

# 3. 設定エリア
st.markdown("---")
with st.expander("⚙️ オプション設定", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        var_ruby = st.checkbox("ルビを削除する", value=True)
        var_images = st.checkbox("画像を抽出する(zip出力)", value=False)
        var_newline = st.checkbox("改行を削除")
        
    with col2:
        # 【BUG FIX】index=3 は範囲外なので 2 に修正
        var_blank_mode = st.radio(
            "空行(連続改行)の扱い",
            ["そのまま", "1行に統合", "完全削除"],
            index=2
        )
    
    st.divider()

    use_wrap = st.toggle("指定文字数で改行", value=False)
    var_width = st.slider("文字数", 1, 100, 15, disabled=not use_wrap)
    
    if not use_wrap:
        var_width = 0

# --- 4. 実行処理ブロック ---
if run_pressed and uploaded_files:
    
    # 【CODE FIX】重複定義を削除し、正しいロジックのみ残す
    is_single_txt = len(uploaded_files) == 1 and not var_images

    zip_buffer = io.BytesIO()
    single_txt_data = ""
    single_filename = ""
    
    with result_container:
        progress_bar = st.progress(0)
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            
            for i, file in enumerate(uploaded_files):
                # 【BUG FIX】UIの選択肢とロジックの不整合を解消
                logic_blank_mode = var_blank_mode
                if var_blank_mode == "完全削除":
                    logic_blank_mode = "完全に詰める"

                options = {
                    'remove_ruby': var_ruby,
                    'remove_newlines': var_newline,
                    'blank_mode': logic_blank_mode, # マッピング後の値を使用
                    'save_images': var_images,
                    'wrap_width': var_width
                }
                
                txt, imgs = convert_epub_logic(file, options)
                
                if txt:
                    base_name = file.name.replace(".epub", "")
                    
                    if is_single_txt:
                        single_txt_data = txt
                        single_filename = f"{base_name}.txt"
                    
                    zip_file.writestr(f"{base_name}.txt", txt)
                    
                    if imgs:
                        for img_name, img_data in imgs:
                            # 画像パスのセパレータ問題を回避するためファイル名のみ抽出する処理を入れても良いが
                            # ここではそのままパスとして使用（ZipFileは階層構造を許容するためOK）
                            zip_file.writestr(f"{base_name}_images/{img_name}", img_data)
                
                progress_bar.progress((i + 1) / len(uploaded_files))
    
    # --- 結果表示 ---
    with result_container:
        st.success("変換完了！")
        
        if is_single_txt:
            st.download_button(
                label="📄 テキスト形式で保存 (.txt)",
                data=single_txt_data,
                file_name=single_filename,
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.download_button(
                label="📦 まとめてダウンロード (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="converted_files.zip",
                mime="application/zip",
                use_container_width=True
            )
        st.markdown("---")

# --- 5. フッター ---
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
