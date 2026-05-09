# LogAI Installation and Setup for Morphic

## ✅ Installation Status

**LogAI by Salesforce**: Successfully installed
- **Version**: 0.1.5
- **Installation Path**: `/home/rohan/Public/morphic/backend/venv/lib/python3.12/site-packages/logai/`
- **Virtual Environment**: Created and activated

## 📦 Installed Components

### Core LogAI Library
- `logai==0.1.5` - Main library
- NLTK punkt data - Downloaded and available

### Key Dependencies Installed
- `pandas==2.2.3` - Data manipulation
- `numpy==1.26.4` - Numerical computing
- `scikit-learn==1.8.0` - Machine learning
- `scipy==1.17.1` - Scientific computing
- `matplotlib==3.10.9` - Visualization
- `seaborn==0.13.2` - Statistical visualization
- `plotly==6.7.0` - Interactive plots
- `spacy==3.8.14` - NLP processing
- `gensim==4.4.0` - Topic modeling
- `prophet==1.3.0` - Time series forecasting
- `lightgbm==4.6.0` - Gradient boosting
- `salesforce-merlion==2.0.4` - Time series analysis

## 🗂️ Available LogAI Modules

The following modules are available in the installed LogAI package:

```
logai/
├── applications/          # Application-specific implementations
├── algorithms/           # Core algorithms
├── analysis/            # Analysis utilities
├── config_interfaces.py  # Configuration interfaces
├── dataloader/          # Data loading utilities
├── information_extraction/  # Information extraction
├── preprocess/          # Data preprocessing
└── utils/               # Utility functions
```

## 🔧 Usage Examples

### Basic Log Processing
```python
import logai
import pandas as pd

# Load log data
logs = pd.read_csv('your_logs.csv')

# Basic analysis using LogAI utilities
from logai.utils import log_utils
processed_logs = log_utils.clean_log_data(logs)
```

### Anomaly Detection
```python
from logai.algorithms import anomaly_detection

# Initialize anomaly detector
detector = anomaly_detection.LogAnomalyDetector()

# Detect anomalies in log patterns
anomalies = detector.fit_predict(logs)
```

### Pattern Extraction
```python
from logai.information_extraction import pattern_extraction

# Extract log patterns
extractor = pattern_extraction.LogPatternExtractor()
patterns = extractor.extract_patterns(logs)
```

## 🚀 Integration with Morphic

### For Incident Analysis
```python
# In your incident processing pipeline
import logai
from logai import analysis

def analyze_incident_logs(log_data):
    """Use LogAI to analyze incident logs"""
    # Preprocess logs
    processed = logai.preprocess.clean_logs(log_data)
    
    # Extract patterns
    patterns = logai.information_extraction.extract_patterns(processed)
    
    # Detect anomalies
    anomalies = logai.algorithms.detect_anomalies(processed)
    
    return {
        'patterns': patterns,
        'anomalies': anomalies,
        'processed_logs': processed
    }
```

### For Root Cause Analysis
```python
def perform_rca_with_logai(trace_logs):
    """Enhanced RCA using LogAI"""
    # Time series analysis for temporal patterns
    temporal_analysis = logai.analysis.temporal_analysis(trace_logs)
    
    # Correlation analysis
    correlations = logai.analysis.correlation_analysis(trace_logs)
    
    # Pattern clustering
    clusters = logai.analysis.cluster_patterns(trace_logs)
    
    return {
        'temporal_patterns': temporal_analysis,
        'correlations': correlations,
        'pattern_clusters': clusters
    }
```

## 📚 Documentation References

- **Official Documentation**: https://opensource.salesforce.com/logai/
- **GitHub Repository**: https://github.com/salesforce/logai
- **Technical Paper**: Available in the repository

## ⚠️ Known Issues & Solutions

### Issue: Missing Rust Compiler
**Problem**: Some dependencies require Rust compiler
**Solution**: Install Rust using `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y`

### Issue: NLTK Data Missing
**Problem**: `Resource punkt not found` error
**Solution**: Run `python -m nltk.downloader punkt`

### Issue: Deep Learning Dependencies
**Problem**: Deep learning models require additional packages
**Solution**: Install with `pip install "logai[deep-learning]"` (requires Rust)

## 🔄 Virtual Environment Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Deactivate virtual environment
deactivate

# Install additional packages
pip install package-name

# Export requirements
pip freeze > requirements.txt

# Install from requirements
pip install -r requirements.txt
```

## 🎯 Next Steps for Morphic Integration

1. **Create LogAI Service Module**: Build wrapper functions for LogAI functionality
2. **Integrate with Incident Pipeline**: Use LogAI for log analysis in incident processing
3. **Enhance RCA**: Leverage LogAI's pattern extraction for better root cause analysis
4. **Add Anomaly Detection**: Implement real-time anomaly detection using LogAI algorithms
5. **Build Visualization**: Use LogAI's plotting capabilities for incident visualization

## 📝 Environment Variables

Add these to your `.env` file:

```env
# LogAI Configuration
LOGAI_CACHE_DIR=/tmp/logai_cache
LOGAI_MODEL_DIR=/tmp/logai_models
LOGAI_NLTK_DATA=/home/rohan/nltk_data
```
