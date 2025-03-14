from pathlib import Path
import sqlite3
import re
import os

class ChineseDictionary:
    # Pinyin tone marks mapping
    _TONE_MARKS = {
        'a': 'āáǎà',
        'e': 'ēéěè',
        'i': 'īíǐì',
        'o': 'ōóǒò',
        'u': 'ūúǔù',
        'ü': 'ǖǘǚǜ',
        'v': 'ǖǘǚǜ'  # v is used as ü in pinyin numbers
    }
    
    # Order of vowels to check for adding tone marks
    _VOWEL_PRIORITY = ['a', 'e', 'o', 'i', 'u', 'v']
    
    def __init__(self, db_path=None):
        if db_path is None:
            # Get the tutorials directory as project root
            project_root = Path(__file__).parent
            db_path = project_root / "data" / "dictionary.db"
        self.db_path = db_path
        self._ensure_db()
    
    def _ensure_db(self):
        """Create the database and load dictionary if needed"""
        if not Path(self.db_path).exists():
            print(f"Creating new dictionary database at {self.db_path}")
            self._create_db()
            self._load_cedict()
        else:
            print(f"Using existing dictionary database at {self.db_path}")
    
    def _create_db(self):
        """Create the SQLite database schema"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            traditional TEXT,
            simplified TEXT,
            pinyin TEXT,
            definitions TEXT,
            PRIMARY KEY (simplified, traditional)
        )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_simplified ON entries(simplified)')
        conn.commit()
        conn.close()
    
    def _load_cedict(self):
        """Load CC-CEDICT data into SQLite database"""
        # Get the tutorials directory as project root
        project_root = Path(__file__).parent
        cedict_path = project_root / "data" / "cedict.txt"
        
        if not cedict_path.exists():
            raise FileNotFoundError(f"CC-CEDICT file not found at {cedict_path}. Please ensure cedict.txt is in the tutorials/data directory.")
        
        print(f"Loading dictionary data from {cedict_path}")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # CC-CEDICT line format: traditional simplified [pinyin] /definition 1/definition 2/
        pattern = re.compile(r'^(\S+)\s+(\S+)\s+\[(.*?)\]\s+/(.+)/$')
        
        with open(cedict_path, 'r', encoding='utf-8') as f:
            entries = []
            total_entries = 0
            
            for line in f:
                if line.startswith('#'):
                    continue
                    
                match = pattern.match(line.strip())
                if match:
                    trad, simp, pinyin, defs = match.groups()
                    entries.append((trad, simp, pinyin, defs))
                    total_entries += 1
                
                # Batch insert every 1000 entries
                if len(entries) >= 1000:
                    c.executemany('INSERT OR REPLACE INTO entries VALUES (?,?,?,?)', entries)
                    entries = []
            
            # Insert any remaining entries
            if entries:
                c.executemany('INSERT OR REPLACE INTO entries VALUES (?,?,?,?)', entries)
        
        print(f"Loaded {total_entries} dictionary entries")
        conn.commit()
        conn.close()
    
    def _convert_pinyin(self, pinyin):
        """Convert numbered pinyin to pinyin with tone marks"""
        # Remove any spaces to handle each word separately
        words = pinyin.split()
        result = []
        
        for word in words:
            # If there's no tone number, keep as is
            if not any(c.isdigit() for c in word):
                result.append(word)
                continue
                
            # Extract tone number and remove it
            tone = int(re.findall(r'\d', word)[0])
            base = re.sub(r'\d', '', word)
            
            # Handle 'u:' or 'v' to 'ü'
            base = base.replace('u:', 'ü').replace('v', 'ü')
            
            # Find the vowel to modify based on priority
            vowel_index = -1
            vowel_to_change = 'a'
            
            for v in self._VOWEL_PRIORITY:
                if v in base:
                    vowel_index = base.index(v)
                    vowel_to_change = v
                    break
            
            if vowel_index >= 0:
                # Handle special case for 'ü'
                if vowel_to_change == 'ü':
                    vowel_to_change = 'v'
                # Get the tone marked vowel
                tone_index = tone - 1 if tone > 0 else 0
                tone_vowel = self._TONE_MARKS[vowel_to_change][tone_index]
                # Replace the vowel with tone marked version
                if vowel_to_change == 'v':
                    tone_vowel = tone_vowel.replace('v', 'ü')
                base = base[:vowel_index] + tone_vowel + base[vowel_index + 1:]
            
            result.append(base)
        
        return ' '.join(result)

    def lookup(self, word):
        """Look up a word in the dictionary"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Try exact match first
        c.execute('SELECT * FROM entries WHERE simplified=? OR traditional=?', (word, word))
        result = c.fetchone()
        
        if not result and len(word) > 1:
            components = []
            i = 0
            while i < len(word):
                # Try to match two characters first if possible
                pair_match = None
                if i + 1 < len(word):
                    pair = word[i:i+2]
                    c.execute('SELECT * FROM entries WHERE simplified=? OR traditional=?', (pair, pair))
                    pair_match = c.fetchone()
                
                if pair_match:
                    # If we found a two-character match, use it
                    components.append({
                        'traditional': pair_match[0],
                        'simplified': pair_match[1],
                        'pinyin': self._convert_pinyin(pair_match[2]),
                        'definitions': pair_match[3].split('/'),
                        'is_pair': True
                    })
                    i += 2
                else:
                    # Fall back to single character
                    c.execute('SELECT * FROM entries WHERE simplified=? OR traditional=?', (word[i], word[i]))
                    char_result = c.fetchone()
                    if char_result:
                        components.append({
                            'traditional': char_result[0],
                            'simplified': char_result[1],
                            'pinyin': self._convert_pinyin(char_result[2]),
                            'definitions': char_result[3].split('/'),
                            'is_pair': False
                        })
                    i += 1
            
            if components:
                # Create a more descriptive combined definition
                definitions = []
                if len(components) > 1:
                    # Group the definitions based on whether they came from pairs or singles
                    parts = []
                    for comp in components:
                        if comp['is_pair']:
                            parts.append(f"{comp['simplified']} ({comp['definitions'][0]})")
                        else:
                            parts.append(f"{comp['simplified']} ({comp['definitions'][0]})")
                    definitions.append(f"Word breakdown: {' + '.join(parts)}")
                
                combined = {
                    'traditional': ''.join(c['traditional'] for c in components),
                    'simplified': ''.join(c['simplified'] for c in components),
                    'pinyin': ' '.join(c['pinyin'] for c in components),
                    'definitions': definitions
                }
                
                # Add note about compound word
                if word != combined['simplified']:
                    combined['definitions'].append(f"Note: This is a compound word broken down into components.")
                
                conn.close()
                return combined
        
        conn.close()
        
        if result:
            trad, simp, pinyin, definitions = result
            return {
                'traditional': trad,
                'simplified': simp,
                'pinyin': self._convert_pinyin(pinyin),
                'definitions': definitions.split('/')
            }
        return None 