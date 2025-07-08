#!/bin/bash

echo "📦 Exporting conda env to environment.yaml"
conda env export --no-builds > environment.yaml

echo "🐍 Exporting pip deps to requirements.txt"
pip freeze > requirements.txt

echo "✅ Done."
