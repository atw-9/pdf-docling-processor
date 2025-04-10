import os
import uuid
import logging
import re # Import regular expressions
from flask import (
    Flask, request, render_template, redirect, url_for,
    send_from_directory, flash, get_flashed_messages, jsonify
)
from werkzeug.utils import secure_filename
# Adjust these imports based on your specific docling installation/structure
from docling.datamodel.base_models import FigureElement, InputFormat, Table
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import ImageRefMode, PictureItem, TableItem
from pathlib import Path
import shutil

# --- Configuration --- (Keep your existing config)
UPLOAD_FOLDER = 'uploads'
OUTPUT_MD_FOLDER = 'output_md'
IMAGE_FOLDER_RELATIVE = os.path.join('static', 'images') # Relative path for url_for
IMAGE_FOLDER_ABSOLUTE = os.path.abspath(IMAGE_FOLDER_RELATIVE)
IMAGE_BASE_URL = "http://localhost:5000" # !!! CHANGE THIS AS NEEDED !!!
ALLOWED_EXTENSIONS = {'pdf'}
CLEANUP_ARTIFACTS = True # Keep True to remove the _artifacts folder

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_MD_FOLDER'] = OUTPUT_MD_FOLDER
app.config['IMAGE_FOLDER'] = IMAGE_FOLDER_ABSOLUTE
app.secret_key = 'replace_with_a_very_secure_secret_key_too'

logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(__name__)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_MD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_FOLDER_ABSOLUTE, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', image_base_url=IMAGE_BASE_URL)

@app.route('/convert', methods=['POST'])
def convert_files():
    if 'files[]' not in request.files:
        return jsonify({"success": False, "message": "No file part in the request."}), 400

    files = request.files.getlist('files[]')
    if not files or files[0].filename == '':
        return jsonify({"success": False, "message": "No files selected for upload."}), 400

    converted_files_info = []
    errors = []

    for file in files:
        if file and allowed_file(file.filename):
            pdf_filename_secure = secure_filename(file.filename)
            pdf_basename = os.path.splitext(pdf_filename_secure)[0]
            pdf_filepath = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename_secure)

            md_filename = f"{pdf_basename}.md"
            md_filepath = os.path.join(app.config['OUTPUT_MD_FOLDER'], md_filename)
            doc_image_subdir_relative = os.path.join('images', pdf_basename)
            doc_image_subdir_absolute = os.path.join(IMAGE_FOLDER_ABSOLUTE, pdf_basename)
            os.makedirs(doc_image_subdir_absolute, exist_ok=True)
            artifact_dir_name = f"{pdf_basename}.md_artifacts"
            artifact_dir_path_absolute = os.path.join(app.config['OUTPUT_MD_FOLDER'], artifact_dir_name)

            try:
                file.save(pdf_filepath)
                _log.info(f"Processing uploaded file: {pdf_filepath}")

                pipeline_options = PdfPipelineOptions()
                pipeline_options.images_scale = 2.0
                pipeline_options.generate_picture_images = True

                doc_converter = DocumentConverter(
                    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
                )

                conv_res = doc_converter.convert(pdf_filepath)
                doc = conv_res.document

                _log.info(f"Saving extracted images for {pdf_basename} and building URL map...")
                image_ref_to_url_map = {}
                picture_counter = 0

                for element, _level in doc.iterate_items():
                    if isinstance(element, PictureItem) and getattr(element, 'image', None) and getattr(element.image, 'pil_image', None):
                        picture_counter += 1
                        try:
                            sanitized_ref = element.self_ref.replace('/', '_').replace('#', '')
                            safe_base_filename = secure_filename(sanitized_ref or f'image_{picture_counter}')
                            unique_img_filename = f"{uuid.uuid4()}_{safe_base_filename}.png"
                            saved_image_path = os.path.join(doc_image_subdir_absolute, unique_img_filename)

                            element.image.pil_image.save(saved_image_path, format="PNG")
                            _log.debug(f"Saved extracted image: {saved_image_path}")

                            image_static_path = f"{doc_image_subdir_relative}/{unique_img_filename}"
                            image_url = f"{IMAGE_BASE_URL}{url_for('static', filename=image_static_path)}"

                            # --- Store the mapping: self_ref -> http_url ---
                            image_ref_to_url_map[element.self_ref] = image_url

                        except AttributeError as pil_err:
                            _log.warning(f"Skipping image {element.self_ref}: No PIL image data available ({pil_err})")
                        except Exception as img_err:
                            _log.error(f"Could not save image {element.self_ref}: {img_err}")
                    elif isinstance(element, PictureItem):
                         _log.warning(f"Skipping picture item {element.self_ref}: No image data found.")

                # --- Save Markdown using REFERENCED mode ---
                _log.info(f"Saving initial Markdown with relative artifact paths to {md_filepath}...")
                doc.save_as_markdown(md_filepath, image_mode=ImageRefMode.REFERENCED)

                # --- Read the generated Markdown and replace paths ---
                _log.info(f"Reading Markdown and replacing references with web URLs...")
                with open(md_filepath, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()

                final_markdown = markdown_content
                # Regex to find markdown image tags: ![alt text](source)
                img_pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')

                def replace_match_simple(match):
                    alt_text = match.group(1)
                    original_source = match.group(2)
                    _log.debug(f"Checking image tag: alt='{alt_text}', src='{original_source}'")

                    # --- SIMPLIFIED REPLACEMENT LOGIC ---
                    # Check if the original_source exactly matches a key in our map
                    # (Assuming docling uses the self_ref as the source in REFERENCED mode)
                    if original_source in image_ref_to_url_map:
                        new_url = image_ref_to_url_map[original_source]
                        _log.info(f"  Replacing reference '{original_source}' with URL '{new_url}'")
                        return f"![{alt_text}]({new_url})"
                    else:
                        # ALSO CHECK if the source is an artifact path we need to map back
                        # (This covers the case where REFERENCED *does* create artifact paths)
                        match_index = re.search(r'image_(\d+)[_.]', original_source)
                        if not match_index:
                            match_index = re.search(r'image_(\d+)$', original_source.rsplit('.', 1)[0])

                        if match_index:
                           index_str = match_index.group(1)
                           index = int(index_str)
                           self_ref_key = f"#/pictures/{index}"
                           _log.debug(f"  Attempting artifact mapping: index={index}, key='{self_ref_key}'")
                           if self_ref_key in image_ref_to_url_map:
                                new_url = image_ref_to_url_map[self_ref_key]
                                _log.info(f"  Replacing artifact path '{original_source}' with URL '{new_url}'")
                                return f"![{alt_text}]({new_url})"
                           else:
                                _log.warning(f"  Mapping failed for artifact: self_ref key '{self_ref_key}' not found for source '{original_source}'")
                                _log.debug(f"  Available map keys: {list(image_ref_to_url_map.keys())}")
                        else:
                            _log.warning(f"  Source '{original_source}' is not a mapped self_ref or a recognized artifact path. Leaving link unchanged.")

                    # If no replacement happened, return the original tag
                    return match.group(0)

                # Perform the replacement using the new simple function
                final_markdown = img_pattern.sub(replace_match_simple, markdown_content)

                # --- Save Final Modified Markdown ---
                with open(md_filepath, 'w', encoding='utf-8') as f:
                    f.write(final_markdown)
                _log.info(f"Saved final Markdown: {md_filepath}")
                converted_files_info.append({
                    "name": md_filename,
                    "url": url_for('download_md', filename=md_filename)
                })

                # --- Optional: Clean up the _artifacts directory ---
                if CLEANUP_ARTIFACTS and os.path.exists(artifact_dir_path_absolute):
                    try:
                        shutil.rmtree(artifact_dir_path_absolute)
                        _log.info(f"Removed artifacts directory: {artifact_dir_path_absolute}")
                    except OSError as rm_err:
                        _log.warning(f"Could not remove artifacts directory {artifact_dir_path_absolute}: {rm_err}")

            except Exception as e:
                _log.error(f"Failed processing {pdf_filename_secure}: {e}", exc_info=True)
                errors.append(f"Error converting {pdf_filename_secure}: {e}")
            finally:
                if os.path.exists(pdf_filepath):
                    try: os.remove(pdf_filepath)
                    except OSError: pass
                    _log.info(f"Removed uploaded file: {pdf_filepath}")

        elif file:
             errors.append(f"File type not allowed for {secure_filename(file.filename)}")

    if not errors and converted_files_info:
        return jsonify({"success": True, "files": converted_files_info})
    elif errors:
        error_message = "; ".join(errors)
        if converted_files_info:
             return jsonify({"success": True, "files": converted_files_info, "message": f"Partial success. Errors: {error_message}"})
        else:
            return jsonify({"success": False, "message": error_message}), 400
    else:
        return jsonify({"success": False, "message": "No valid PDF files found to convert."}), 400


@app.route('/download_md/<path:filename>')
def download_md(filename):
    safe_filename = secure_filename(filename)
    directory = os.path.abspath(app.config['OUTPUT_MD_FOLDER'])
    file_path = os.path.join(directory, safe_filename)
    if not os.path.abspath(file_path).startswith(directory):
         return "Access Denied", 403
    try:
        return send_from_directory(directory, safe_filename, as_attachment=False)
    except FileNotFoundError:
        return "File Not Found", 404

if __name__ == '__main__':
    _log.info(f"--- Server Starting ---")
    _log.info(f"Serving images from: {IMAGE_FOLDER_ABSOLUTE}")
    _log.info(f"Image Base URL for Markdown: {IMAGE_BASE_URL}")
    _log.info(f"Markdown output directory: {OUTPUT_MD_FOLDER}")
    _log.info(f"Server accessible at http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)