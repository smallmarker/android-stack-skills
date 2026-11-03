"""Read upstream Maven metadata without changing pins."""
import urllib.request
import xml.etree.ElementTree as ET

modules = {
 'retrofit': ('https://repo.maven.apache.org/maven2', 'com/squareup/retrofit2/retrofit'),
 'okhttp': ('https://repo.maven.apache.org/maven2', 'com/squareup/okhttp3/okhttp'),
 'coil': ('https://repo.maven.apache.org/maven2', 'io/coil-kt/coil3/coil-compose'),
 'timber': ('https://repo.maven.apache.org/maven2', 'com/jakewharton/timber/timber'),
 'hilt': ('https://repo.maven.apache.org/maven2', 'com/google/dagger/hilt-android'),
 'kotlin': ('https://repo.maven.apache.org/maven2', 'org/jetbrains/kotlin/kotlin-gradle-plugin'),
 'serialization': ('https://repo.maven.apache.org/maven2', 'org/jetbrains/kotlinx/kotlinx-serialization-json'),
 'agp': ('https://dl.google.com/dl/android/maven2', 'com/android/tools/build/gradle'),
 'compose-bom': ('https://dl.google.com/dl/android/maven2', 'androidx/compose/compose-bom'),
}
for name, (base, path) in modules.items():
    url = f'{base}/{path}/maven-metadata.xml'
    try:
        root = ET.fromstring(urllib.request.urlopen(url, timeout=25).read())
        stable = [v.text for v in root.findall('versioning/versions/version') if all(c.isdigit() or c == '.' for c in v.text)]
        print(name, stable[-1], url, flush=True)
    except Exception as exc:
        print(name, type(exc).__name__, str(exc), flush=True)
