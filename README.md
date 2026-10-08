# Album art embedder

Embeds album art (album cover) as MP3 metadata. Processes folders recursively, searching for files named "folder.", "cover.", or "album name.". Works for .png, .jpg and .jpeg.

Requires Python 3 and mutagen.

Outputs changes to terminal, and a list of albums for which album art was not embedded or found.

Tested in Windows. Run with

`py embed_art.py "D:\Music"`

or 

`& <path to python> embed_art.py "D:\Music"`

Or test without making changes with

`py embed_art.py "D:\Music" --dry-run`
