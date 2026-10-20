# Datasets

Los archivos no se suben al repositorio (pesan ~700 MB y `postings.csv` de arshkon supera el límite de 100 MB de GitHub).
Descárgalos con la CLI de Kaggle (requiere tu propio token en `~/.kaggle/access_token`):

```bash
pip install kaggle
cd datos
for d in asaniczka/data-analyst-job-postings \
         asaniczka/software-engineer-job-postings-linkedin \
         asaniczka/data-scientist-linkedin-job-postings; do
  kaggle datasets download -d "$d" -p "${d//\//_}" --unzip
done
```

Datasets usados para el catálogo (principales):

- https://www.kaggle.com/datasets/asaniczka/data-analyst-job-postings
- https://www.kaggle.com/datasets/asaniczka/software-engineer-job-postings-linkedin
- https://www.kaggle.com/datasets/asaniczka/data-scientist-linkedin-job-postings

Descargados además como apoyo (opcionales):

- https://www.kaggle.com/datasets/arshkon/linkedin-job-postings
- https://www.kaggle.com/datasets/rajatraj0502/linkedin-job-2023

Revisa la licencia y los términos de uso de cada dataset en su página de Kaggle.
