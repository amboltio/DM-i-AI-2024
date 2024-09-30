from utils import l1_score, plot_prediction, load_sample
from model import predict

PATIENT_IX = "000_0"

sample = load_sample(PATIENT_IX)
tissue_image = sample["tissue_image"]
corrupted_image = sample["corrupted_image"]
mask_image = sample["mask_image"]
ct_image = sample["ct_image"]
vertebrae = sample["vertebrae"]

## Predict reconstruction
reconstructed_image = predict(corrupted_image,tissue_image,mask_image,vertebrae)

# Plot and score prediction
plot_prediction(corrupted_image,tissue_image,mask_image,reconstructed_image,vertebrae,ct_image)
l1 = l1_score(ct_image,corrupted_image)
print(f"L1 score: {l1:.03f}")