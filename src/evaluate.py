import numpy as np

LABELS = ["H", "D", "A"]
LABEL_IDX = {label: i for i, label in enumerate(LABELS)}

def calc_metrics(y_true, y_prob):
    """Verilen gerçek etiketler ve olasılıklar için metrikleri hesaplar."""
    y_true = np.asarray(y_true, dtype=str)
    y_prob = np.asarray(y_prob, dtype=float)
    
    # Geçerli satırları filtrele
    valid = np.isin(y_true, LABELS) & np.isfinite(y_prob).all(axis=1)
    y_true, y_prob = y_true[valid], y_prob[valid]
    
    # Normalize et
    y_prob = y_prob / y_prob.sum(axis=1, keepdims=True)
    
    # İndekslere çevir
    y_idx = np.array([LABEL_IDX[y] for y in y_true])
    
    # Log Loss (Manuel ve kesin hesap)
    chosen_probs = y_prob[np.arange(len(y_idx)), y_idx]
    log_loss = -np.mean(np.log(np.clip(chosen_probs, 1e-15, 1.0)))
    
    # Brier Skoru
    one_hot = np.eye(3)[y_idx]
    brier = np.mean(np.sum((y_prob - one_hot) ** 2, axis=1))
    
    # Accuracy
    acc = np.mean(np.argmax(y_prob, axis=1) == y_idx)
    
    return {
        "log_loss": log_loss,
        "brier": brier,
        "accuracy": acc,
        "n_matches": len(y_true)
    }