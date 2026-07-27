# Formatos soportados / a soportar

Listado de formatos de oficina organizados por prioridad. Se excluyen los
formatos de baja prioridad (propietarios Apple, ebooks, correo, etc.).

Estado de implementación (versión 0.2.0):

| Formato | Estado | Reader | Notas |
|---|---|---|---|
| `.pdf` | ✅ implementado | `readers/pdf.py` | OCR con Tesseract |
| `.png` | ✅ implementado | `readers/images.py` | OCR |
| `.jpg` / `.jpeg` | ✅ implementado | `readers/images.py` | OCR |
| `.bmp` | ✅ implementado | `readers/images.py` | OCR |
| `.webp` | ✅ implementado | `readers/images.py` | OCR |
| `.heic` | ✅ implementado (con `[heic]`) | `readers/images.py` | Requiere `pillow-heif` |
| `.tif` / `.tiff` | ✅ implementado (multi-página) | `readers/images.py` | Una página por frame |
| `.docx` | ✅ implementado | `readers/docx.py` | python-docx, sin OCR |
| `.pptx` | ✅ implementado | `readers/pptx.py` | python-pptx, sin OCR |
| `.xlsx` | ✅ implementado | `readers/xlsx.py` | openpyxl, sin OCR |
| `.doc` | ✅ implementado (con LibreOffice) | `readers/legacy.py` | Convierte a .docx |
| `.xls` | ✅ implementado (con LibreOffice) | `readers/legacy.py` | Convierte a .xlsx |
| `.ppt` | ✅ implementado (con LibreOffice) | `readers/legacy.py` | Convierte a .pptx |

## 🔴 Formatos muy comunes (alta prioridad)

### Documentos de Microsoft Office
| Formato | Descripción | Notas |
|---|---|---|
| **`.pdf`** | PDF | Ya soportado |
| **`.docx`** | Word moderno (2007+) | El más usado en oficinas |
| **`.doc`** | Word antiguo (97-2003) | Muy común aún en empresas |
| **`.xlsx`** | Excel moderno | Celdas, tablas, fórmulas |
| **`.xls`** | Excel antiguo | Legado pero presente |
| **`.pptx`** | PowerPoint moderno | Presentaciones |
| **`.ppt`** | PowerPoint antiguo | Legado |

### Imágenes (OCR directo)
| Formato | Descripción |
|---|---|
| **`.png`** | Común en capturas y escaneos |
| **`.jpg` / `.jpeg`** | Fotos y escaneos |
| **`.tiff` / `.tif`** | Escaneos profesionales (estándar en OCR) |
| **`.bmp`** | Sin comprimir (legado) |
| **`.webp`** | Web moderno |
| **`.heic` / `.heif`** | iPhone (cada vez más común) |

## 🟡 Formatos comunes (media prioridad)

### OpenDocument / LibreOffice
| Formato | Descripción |
|---|---|
| **`.odt`** | Texto (alternativa open source a Word) |
| **`.ods`** | Hojas de cálculo (alternativa a Excel) |
| **`.odp`** | Presentaciones (alternativa a PowerPoint) |

### Texto plano y enriquecido
| Formato | Descripción |
|---|---|
| **`.txt`** | Texto plano |
| **`.rtf`** | Rich Text Format (legado pero presente) |
| **`.md`** | Markdown (común en tech) |
| **`.csv`** | Datos tabulares separados por comas |
| **`.tsv`** | Datos tabulares separados por tabuladores |

## 💡 Notas de implementación

1. **Texto embebido** (`.docx`, `.xlsx`, `.pptx`, `.odt`, `.txt`, `.csv`, `.md`, `.rtf`):
   se extrae texto directamente sin OCR, son rápidos.
2. **OCR necesario** (`.pdf`, imágenes como `.png`, `.jpg`, `.tiff`): pasan por
   Tesseract. Soportar **TIF/TIFF** es especialmente importante porque es el
   formato estándar de escaneo.
3. **Formatos antiguos** (`.doc`, `.xls`, `.ppt`): convertidos vía
   LibreOffice headless al formato moderno equivalente, y luego procesados
   con el reader moderno.

## 🚀 Roadmap

Próximos formatos a soportar (no incluidos aún):

- **OpenDocument** (`.odt`, `.ods`, `.odp`) — `odfpy`
- **Texto** (`.txt`, `.md`, `.csv`, `.tsv`, `.rtf`) — readers ligeros

## 📝 Nota sobre coma

El `clean_line` por defecto **no incluye la coma** en el conjunto
permitido (`a-zA-Z0-9 '-.!?`). Esto significa que las comas en la salida
OCR se reemplazan por espacios. Si necesitas conservar comas, edita el
`allowed` set en `ocr_extractor/core.py` y reinstala (`pip install -e .`).
Los formatos Office modernos (`.docx`/`.pptx`/`.xlsx`) **no** pasan por
`clean_line`, así que sus comas sí se preservan.