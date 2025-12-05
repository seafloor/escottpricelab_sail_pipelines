# Escott-Price Lab SAIL Pipelines

Minimal pipelines and notebooks for standard operations in health care data, especially the SAIL Databank or other UK EHR databases.

At the moment, main usage is for pulling ICD-10 and NHS read codes v2 from the HDR UK library.

## 📦 Installation

This project is managed with `uv` - install it [here](https://docs.astral.sh/uv/getting-started/installation/).

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/seafloor/escottpricelab_sail_pipelines
    cd escottpricelab_sail_pipelines
    ```

2.  **Create environment and install dependencies:**
    ```bash
    uv venv
    uv sync
    ```

## 💻 Usage

Get phenotype codes from [HDR UK Phenotype Library](https://phenotypes.healthdatagateway.org/). Examples here are from the CALIBER network. Extract the corresponding codes with 

```bash
uv run pull_codes.py
```

Example usage will go in /notebooks. You can run through jupyterlab as:

```bash
uv run --with jupyter jupyter lab
```

## Further information

See the CALIBER paper:
["UK phenomics platform for developing and validating electronic health record phenotypes: CALIBER", Denaxas et al., Journal of the American Medical Informatics Association, Volume 26, Issue 12, December 2019, Pages 1545–1559](https://doi.org/10.1093/jamia/ocz105)

See also the [HDR UK data gateway](https://phenotypes.healthdatagateway.org/).



## License

This project is licensed under the MIT License.