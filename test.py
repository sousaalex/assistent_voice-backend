import os

os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

import shutil
print(shutil.which("ffmpeg"))  # Deve mostrar o caminho completo agora

# seu código whisper aqui
