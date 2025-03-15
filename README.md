# Chinese Reader

A web-based tool for reading Chinese text with integrated dictionary lookup and word saving functionality. Built with FastHTML and HTMX.

## Features

- **Text Segmentation**: Automatically segments Chinese text into individual words using the Jieba library
- **Interactive Dictionary**: Click on any word to see its:
  - Simplified Chinese form
  - Traditional Chinese form (when different)
  - Pinyin pronunciation
  - English definitions
- **Word Saving**: Save interesting words for later review
- **Pagination**: Handles long texts by breaking them into manageable pages
- **Responsive Design**: Works well on both desktop and mobile devices

## Installation

1. Clone the repository:
```bash
git clone https://github.com/rtarik/chinese-reader.git
cd chinese-reader
```

2. Install dependencies:
```bash
pip install python-fasthtml jieba
```

## Usage

1. Start the server:
```bash
python main.py
```

2. Open your browser and navigate to `http://localhost:5001`

3. Paste any Chinese text into the text area and click "Submit"

4. Click on any word to see its definition

5. Use the "Save" button to save words for later review

6. Navigate between pages using the pagination controls if your text is long

7. View your saved words by clicking "View Saved Words"

## Project Structure

- `main.py`: Main application file with routing and UI components
- `dictionary.py`: Chinese dictionary implementation
- `db.py`: Database operations for saved words
- `static/styles.css`: Custom styling
- `saved_words.py`: Saved words functionality

## Technologies Used

- [FastHTML](https://fastht.ml/): Server-side rendering and routing
- [HTMX](https://htmx.org/): Dynamic UI updates without JavaScript
- [Jieba](https://github.com/fxsjy/jieba): Chinese text segmentation
- PicoCSS: Minimal CSS framework for clean styling

## Contributing

Feel free to open issues or submit pull requests if you have suggestions for improvements or find any bugs.

## License

MIT License - feel free to use this project however you'd like! 