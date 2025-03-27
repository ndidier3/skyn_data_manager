# Development Setup Guide

## 📂 Reference File
To get started, refer to:  
**`App/SDM/Scripts/Test/default_analysis.py`**

---

## Recommended Development Setup
### Environment & Tools
- **Conda** (for environment management)  
- **VS Code** (recommended editor)  
- **Git** (for version control)  
- **Python 3.8.8**  

#### **Create & Activate a Conda Environment**
```sh
conda create --name sdm-env python=3.8.8
conda activate sdm-env
```

#### **Install Dependencies in This Order**
```sh
conda install --file requirements.txt
conda install -c conda-forge kneed=0.7.0 
conda install -c conda-forge scikit-learn=1.3.0
```
