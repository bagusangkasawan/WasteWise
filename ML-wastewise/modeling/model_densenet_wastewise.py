# -*- coding: utf-8 -*-
"""Model_DenseNet_wastewise.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1xyw5h5K0WYZrPPp-tPoi_AIQzWgssp_a
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau, Callback
from tensorflow.keras import mixed_precision
from tensorflow.keras.applications import DenseNet121
from tensorflow.keras.models import Model
from tensorflow.keras.layers import GlobalAveragePooling2D, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix

# prompt: cek versi tensorflow

tf.__version__

from google.colab import drive
drive.mount('/content/drive')

!cp /content/drive/MyDrive/Coba_sandi/data-final.zip /content/
!unzip -q /content/data-final.zip -d /content/data-final

path = '/content/data-final'

TRAIN_DIR = os.path.join(path, 'train')
TEST_DIR = os.path.join(path, 'test')
VAL_DIR = os.path.join(path, 'val')

train_datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=20,
    width_shift_range=0.1,
    height_shift_range=0.1,
    zoom_range=0.2,
    shear_range=0.1,
    horizontal_flip=True,
    fill_mode='nearest'
)

val_test_datagen = ImageDataGenerator(rescale=1./255)

train_generator = train_datagen.flow_from_directory(
    TRAIN_DIR,
    target_size=(224, 224),
    batch_size=64,
    class_mode='categorical'
)

val_generator = val_test_datagen.flow_from_directory(
    VAL_DIR,
    target_size=(224, 224),
    batch_size=64,
    class_mode='categorical'
)

test_generator = val_test_datagen.flow_from_directory(
    TEST_DIR,
    target_size=(224, 224),
    batch_size=64,
    class_mode='categorical',
    shuffle=False
)

# Simpan ke Google Drive (jika pakai Colab)
save_dir = '/content/drive/MyDrive/Coba_sandi/model_dense95'
os.makedirs(save_dir, exist_ok=True)

model_path = os.path.join(save_dir, 'model_checkpoint.h5')

# Callback untuk stop jika akurasi training & val >= 90%
class StopWhenTrainValAccAbove90(Callback):
    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        train_acc = logs.get("accuracy") or logs.get("acc")
        val_acc = logs.get("val_accuracy") or logs.get("val_acc")

        if train_acc is not None and val_acc is not None:
            if train_acc >= 0.95 and val_acc >= 0.95:
                print(f"\n✅ Training dihentikan di epoch {epoch+1} karena accuracy dan val_accuracy >= 95%")
                self.model.stop_training = True

# Callback untuk menyimpan model
checkpoint_callback = ModelCheckpoint(
    filepath=model_path,
    monitor='val_accuracy',
    save_best_only=False,
    save_weights_only=False,
    verbose=1
)

callbacks_list = [
    StopWhenTrainValAccAbove90(),
    checkpoint_callback
]

# MODEL dengan input 224x224 (default DenseNet)
base_model = DenseNet121(
    input_shape=(224, 224, 3),  # Ubah dari 128x128 ke 224x224
    include_top=False,
    weights='imagenet'
)
base_model.trainable = False  # Freeze awal

# Top layer
x = base_model.output
x = GlobalAveragePooling2D()(x)
x = Dense(256, activation='relu')(x)
x = Dropout(0.5)(x)
x = Dense(128, activation='relu')(x)
x = Dropout(0.3)(x)
outputs = Dense(12, activation='softmax')(x)  # ganti sesuai jumlah kelas

model = Model(inputs=base_model.input, outputs=outputs)

# Compile
model.compile(
    optimizer=Adam(learning_rate=1e-3),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# Summary
model.summary()

class_name = list(train_generator.class_indices.keys())

class_weights = compute_class_weight(
    class_weight='balanced',
    classes=np.unique(train_generator.classes),
    y=train_generator.classes
)
class_weights = dict(enumerate(class_weights))

model.fit(
    train_generator,
    validation_data=val_generator,
    epochs=2,  # training awal
    callbacks=callbacks_list,
    class_weight=class_weights
)

# 🔧 FINE-TUNING
# =======================
# Unfreeze base model
base_model.trainable = True

# Hanya buka 50 layer terakhir
for layer in base_model.layers[:-50]:
    layer.trainable = False

# Re-compile model untuk fine-tuning
model.compile(
    optimizer=Adam(learning_rate=1e-4),  # learning rate kecil saat fine-tuning
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

model.fit(
    train_generator,
    validation_data=val_generator,
    epochs=30,
    callbacks=callbacks_list,
    class_weight=class_weights  # jika dataset tidak seimbang
)

from sklearn.metrics import classification_report, confusion_matrix
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# === PREDIKSI DATA TEST ===
# Pastikan test_generator tidak memiliki shuffle=True saat dibuat
pred_probs = model.predict(test_generator)
y_pred = np.argmax(pred_probs, axis=1)  # Prediksi kelas (int)

# Label asli
y_true = test_generator.classes  # label ground truth (int)

# === NAMA KELAS ===
class_names = list(test_generator.class_indices.keys())

# === CLASSIFICATION REPORT ===
print("🔍 Classification Report:")
print(classification_report(y_true, y_pred, target_names=class_names))

# === CONFUSION MATRIX ===
cm = confusion_matrix(y_true, y_pred)

plt.figure(figsize=(10, 8))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=class_names, yticklabels=class_names)
plt.xlabel("Predicted Label")
plt.ylabel("True Label")
plt.title("Confusion Matrix")
plt.tight_layout()
plt.show()

import io
import json
import numpy as np
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.densenet import preprocess_input
import ipywidgets as widgets
from IPython.display import display

# Mapping label
class_indices = train_generator.class_indices
class_labels = dict((v, k) for k, v in class_indices.items())

# Widget upload
upload = widgets.FileUpload(
    accept='image/*',
    multiple=False
)
display(upload)

# Fungsi inference + JSON output
def predict_to_json(uploaded_file):
    if not uploaded_file:
        print("❌ Tidak ada gambar yang diupload.")
        return

    for fname, file_info in uploaded_file.value.items():
        # Load image from uploaded bytes
        img_bytes = file_info['content']
        img = image.load_img(io.BytesIO(img_bytes), target_size=(224, 224))

        # Preprocess
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)

        # Predict
        preds = model.predict(img_array)
        pred_idx = np.argmax(preds[0])
        pred_label = class_labels[pred_idx]
        confidence = float(preds[0][pred_idx])

        # Output JSON
        result_json = {
            "class": pred_label,
            "confidence": round(confidence, 4)
        }

        print(json.dumps(result_json, indent=2))

# Jalankan saat upload terjadi
upload.observe(lambda change: predict_to_json(upload), names='value')

model.save('/content/drive/MyDrive/Coba_sandi/model_dense95/model_dense.keras')  # Keras native format

model.save('/content/drive/MyDrive/Coba_sandi/model_dense95/model_dense.h5')

# menyimpan dengan format pickle

import pickle

# Path tempat Anda ingin menyimpan model pickle di Google Drive
pickle_save_path = '/content/drive/MyDrive/Coba_sandi/model_dense95/model_dense.pkl'

# Simpan model menggunakan pickle
with open(pickle_save_path, 'wb') as f:
    pickle.dump(model, f)

print(f"✅ Model akhir berhasil disimpan dalam format pickle di: {pickle_save_path}")

import json

# Ambil class indices dari train_generator
label_map = train_generator.class_indices

# Balik mappingnya agar index -> label (untuk prediksi)
index_to_label = {v: k for k, v in label_map.items()}

# Simpan ke JSON
label_json_path = '/content/drive/MyDrive/Coba_sandi/model_dense95/label_map.json'
with open(label_json_path, 'w') as f:
    json.dump(index_to_label, f, indent=4)

print(f"✅ Label mapping disimpan di: {label_json_path}")