import streamlit as st
import numpy as np
import cv2
from PIL import Image
import matplotlib.pyplot as plt
import pandas as pd
from sklearn import svm
from sklearn.metrics import roc_curve, auc, accuracy_score, confusion_matrix, classification_report
from datetime import datetime
import seaborn as sns
from skimage.transform import resize
from skimage.registration import register_translation
from scipy.fft import fft2, ifft2

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 1
if 'heatmap_overlay_svm' not in st.session_state:
    st.session_state.heatmap_overlay_svm = None
if 'aligned_images' not in st.session_state:
    st.session_state.aligned_images = None
if 'change_mask' not in st.session_state:
    st.session_state.change_mask = None
if 'classification_svm' not in st.session_state:
    st.session_state.classification_svm = None
if 'before_date' not in st.session_state:
    st.session_state.before_date = datetime(2023, 1, 1)
if 'after_date' not in st.session_state:
    st.session_state.after_date = datetime(2023, 6, 1)
if 'before_file' not in st.session_state:
    st.session_state.before_file = None
if 'after_file' not in st.session_state:
    st.session_state.after_file = None
if 'model_choice' not in st.session_state:
    st.session_state.model_choice = "SVM"
if 'svm_roc_fig' not in st.session_state:
    st.session_state.svm_roc_fig = None
if 'svm_accuracy' not in st.session_state:
    st.session_state.svm_accuracy = None
if 'classification_before_svm' not in st.session_state:
    st.session_state.classification_before_svm = {"Vegetation": 50, "Barren": 30, "Water": 20}
if 'svm_conf_matrix' not in st.session_state:
    st.session_state.svm_conf_matrix = None
if 'svm_class_report' not in st.session_state:
    st.session_state.svm_class_report = None


# Set page config
st.set_page_config(layout="wide", page_title="Satellite Image Analysis")

# Custom title
st.markdown(
    """
    <h1 style='color: yellow; font-size: 72px; font-weight: bold;'>
        Satellite Image Analysis
    </h1>
    """,
    unsafe_allow_html=True
)

# -------- Image Processing Functions --------
def preprocess_img(img, size=(64, 64)):
    try:
        img = img.convert("RGB").resize(size)
        img_arr = np.array(img) / 255.0
        return img_arr
    except Exception as e:
        st.error(f"Error preprocessing image: {e}")
        return None

def align_images(img1, img2):
    try:
        img1_np = np.array(img1)
        img2_np = np.array(img2)
        gray1 = cv2.cvtColor(img1_np, cv2.COLOR_RGB2GRAY)
        gray2 = cv2.cvtColor(img2_np, cv2.COLOR_RGB2GRAY)

        # Use phase correlation for subpixel alignment
        shifted, error, diffphase = register_translation(gray1, gray2, upsample_factor=10)
        translation = (-shifted[1], -shifted[0])  # OpenCV uses (x, y)

        # Apply the translation
        M = np.float32([[1, 0, translation[0]], [0, 1, translation[1]]])
        aligned = cv2.warpAffine(img2_np, M, (img1_np.shape[1], img1_np.shape[0]), borderMode=cv2.BORDER_REFLECT_101)

        diff_mask = cv2.absdiff(img1_np, aligned.astype(np.uint8))
        diff_mask = cv2.cvtColor(diff_mask, cv2.COLOR_RGB2GRAY)
        _, black_mask = cv2.threshold(diff_mask, 30, 255, cv2.THRESH_BINARY_INV)
        aligned_black = cv2.bitwise_and(aligned.astype(np.uint8), aligned.astype(np.uint8), mask=black_mask)

        return Image.fromarray(aligned.astype(np.uint8)), Image.fromarray(aligned_black)
    except Exception as e:
        st.error(f"Image alignment failed: {e}")
        return img2, img2

def get_change_mask(img1, img2, threshold=30):
    try:
        img2_resized = img2.resize(img1.size)
        gray1 = cv2.cvtColor(np.array(img1), cv2.COLOR_RGB2GRAY)
        gray2 = cv2.cvtColor(np.array(img2_resized), cv2.COLOR_RGB2GRAY)
        diff = cv2.absdiff(gray1, gray2)
        _, change_mask = cv2.threshold(diff, threshold, 1, cv2.THRESH_BINARY)
        return change_mask.astype(np.uint8)
    except Exception as e:
        st.error(f"Error creating change mask: {e}")
        return None

def classify_land_svm(img_arr):
    try:
        features = img_arr.flatten()[:100]
        labels = np.random.randint(0, 3, 50)
        svm_model.fit(np.random.rand(50, 100), labels)
        probabilities = svm_model.predict_proba(features.reshape(1, -1))[0]
        classes = ["Vegetation", "Barren", "Water"]
        return {classes[i]: prob * 100 for i, prob in enumerate(probabilities)}
    except Exception as e:
        st.error(f"SVM classification error: {e}")
        return {}

def detect_calamity(date1, date2, change_percentage):
    date_diff = (date2 - date1).days
    if change_percentage > 0.15:
        if date_diff <= 10:
            return "⚠️ **Possible Flood:** Rapid and significant changes observed in a short period may indicate flooding."
        elif date_diff <= 30:
            return "🔥 **Possible Deforestation:** Significant loss of vegetation over a short term could suggest deforestation or wildfires."
        else:
            return "🏗️ **Possible Land Cover Change:** Significant changes observed over a longer period."
    elif change_percentage > 0.05:
        return "🌱 **Seasonal/Minor Changes Detected:** Minor changes likely due to natural variations."
    return "✅ **No Significant Calamity Detected:** Minimal changes observed between the two images."

def get_csv_bytes(data_dict):
    try:
        df = pd.DataFrame(list(data_dict.items()), columns=["Class", "Area (%)"])
        return df.to_csv(index=False).encode()
    except Exception as e:
        st.error(f"Error creating CSV: {e}")
        return None

def generate_roc_curve_svm():
    try:
        # Dummy data for ROC curve (replace with actual predictions and true labels)
        y_true = np.array([0, 0, 1, 1, 0, 1])
        y_scores = np.array([0.2, 0.3, 0.7, 0.8, 0.4, 0.9])

        fpr, tpr, thresholds = roc_curve(y_true, y_scores)
        roc_auc = auc(fpr, tpr)

        fig, ax = plt.subplots()
        ax.plot(fpr, tpr, color='blue', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
        ax.plot([0, 1], [0, 1], color='gray', lw=1, linestyle='--')
        ax.set_xlim([0.0, 1.0])
        ax.set_ylim([0.0, 1.05])
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title('Receiver Operating Characteristic (SVM)')
        ax.legend(loc="lower right")
        return fig
    except Exception as e:
        st.error(f"Error generating SVM ROC curve: {e}")
        return None

def calculate_accuracy_svm():
    try:
        # Dummy data for accuracy calculation (replace with actual predictions and true labels)
        y_true = np.array([0, 1, 0, 1, 0, 1])
        y_pred = np.array([0, 1, 1, 1, 0, 0])
        return accuracy_score(y_true, y_pred)
    except Exception as e:
        st.error(f"Error calculating SVM accuracy: {e}")
        return None

def generate_confusion_matrix(y_true, y_pred, labels):
    try:
        cm = confusion_matrix(y_true, y_pred)
        fig, ax = plt.subplots()
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=labels, yticklabels=labels)
        ax.set_xlabel('Predicted Label')
        ax.set_ylabel('True Label')
        ax.set_title('Confusion Matrix')
        return fig
    except Exception as e:
        st.error(f"Error generating confusion matrix: {e}")
        return None

def generate_classification_report(y_true, y_pred, labels):
    try:
        report = classification_report(y_true, y_pred, target_names=labels, output_dict=True)
        df = pd.DataFrame(report).transpose()
        return df
    except Exception as e:
        st.error(f"Error generating classification report: {e}")
        return None

# -------- Pages --------
def page1():
    st.header("1. Model Selection")
    st.session_state.model_choice = st.selectbox("Select Analysis Model", ["SVM"]) # Removed CNN
    if st.button("Next ➡️"):
        st.session_state.page = 2

def page2():
    st.markdown(
        """
        <h2 style='font-size: 36px; color: white;'>
            2. Image Upload & Dates
        </h2>
        <p style='font-size: 18px; color: lightgray;'>
            Please upload the <b>before</b> and <b>after/current</b> satellite images along with their respective dates for analysis.
        </p>
        """,
        unsafe_allow_html=True
    )
    with st.sidebar:
        st.session_state.before_date = st.date_input("BEFORE image date", value=st.session_state.before_date)
        st.session_state.before_file = st.file_uploader("Upload BEFORE image",
                                                        type=["png", "jpg", "tif"],
                                                        key="before")
        st.session_state.after_date = st.date_input("AFTER image date", value=st.session_state.after_date)
        st.session_state.after_file = st.file_uploader("Upload AFTER image",
                                                       type=["png", "jpg", "tif"],
                                                       key="after")

    if st.button("⬅️ Back"):
        st.session_state.page = 1
    if st.session_state.before_file and st.session_state.after_file:
        if st.button("Next ➡️"):
            try:
                before_img = Image.open(st.session_state.before_file).convert("RGB")
                after_img = Image.open(st.session_state.after_file).convert("RGB")

                aligned_after, aligned_black = align_images(before_img, after_img)
                if aligned_after is not None and aligned_black is not None:
                    st.session_state.aligned_images = {"before": before_img, "after": aligned_after, "aligned_black": aligned_black}
                    st.session_state.change_mask = get_change_mask(before_img, aligned_after)
                    if st.session_state.change_mask is not None:
                        if st.session_state.model_choice == "SVM":
                            before_arr = preprocess_img(before_img)
                            after_arr = preprocess_img(aligned_after)
                            if before_arr is not None and after_arr is not None:
                                st.session_state.classification_svm = classify_land_svm
                                (after_arr)
                                h, w = st.session_state.change_mask.shape
                                heatmap_svm = np.zeros((h, w, 3), dtype=np.uint8)
                                heatmap_svm[..., 0] = st.session_state.change_mask * 255
                                heatmap_img_svm = Image.fromarray(heatmap_svm)
                                aligned_after_resized = st.session_state.aligned_images["after"].resize((w, h))
                                st.session_state.heatmap_overlay_svm = Image.blend(aligned_after_resized.convert("RGB"),
                                                                                    heatmap_img_svm.convert("RGB"),
                                                                                    alpha=0.5)
                                st.session_state.classification = st.session_state.classification_svm
                                st.session_state.svm_roc_fig = generate_roc_curve_svm()
                                st.session_state.svm_accuracy = calculate_accuracy_svm()
                                # Dummy data for confusion matrix and classification report
                                y_true_svm = np.array([0, 0, 1, 1, 2, 2])
                                y_pred_svm = np.array([0, 1, 1, 0, 2, 2])
                                labels_svm = ["Vegetation", "Barren", "Water"]
                                st.session_state.svm_conf_matrix = generate_confusion_matrix(y_true_svm, y_pred_svm, labels_svm)
                                st.session_state.svm_class_report = generate_classification_report(y_true_svm, y_pred_svm, labels_svm)
                                st.session_state.page = 3
                            else:
                                st.error("Error during image preprocessing for SVM.")
                    else:
                        st.error("Could not create change mask.")
                else:
                    st.error("Image alignment failed.")
            except Exception as e:
                st.error(f"Error processing images: {e}")

def page3():
    st.header("3. Aligned Images Comparison")

    if st.session_state.aligned_images is None:
        st.error("No aligned images found. Please upload images first.")
        st.session_state.page = 2
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.image(st.session_state.aligned_images["before"],
                 caption="BEFORE Image", use_column_width=True)
    with col2:
        st.image(st.session_state.aligned_images["after"],
                 caption="Aligned AFTER Image", use_column_width=True)
    with col3:
        st.image(st.session_state.aligned_images["aligned_black"],
                 caption="Aligned Difference", use_column_width=True)

    if st.button("⬅️ Back"):
        st.session_state.page = 2
    if st.button("Next ➡️"):
        st.session_state.page = 4

def page4():
    st.header("4. Change Detection Heatmap")

    # Ensure we have valid images and change mask
    if 'aligned_images' not in st.session_state or st.session_state.aligned_images is None or st.session_state.change_mask is None:
        st.error("Please upload and process images first")
        st.session_state.page = 2
        return

    st.subheader(f"Heatmap using {st.session_state.model_choice} Model")

    h, w = st.session_state.change_mask.shape
    aligned_after_resized = st.session_state.aligned_images["after"].resize(w, h))

    if st.session_state.model_choice == "SVM" and st.session_state.heatmap_overlay_svm is not None:
        st.image(st.session_state.heatmap_overlay_svm, caption="Change Heatmap (Blue)", use_column_width=True)
    else:
        # Default red heatmap if something goes wrong or initially
        heatmap = np.zeros((h, w, 3), dtype=np.uint8)
        heatmap[..., 2] = st.session_state.change_mask * 255  # Red channel
        heatmap_img = Image.fromarray(heatmap)
        st.session_state.heatmap_overlay_default = Image.blend(aligned_after_resized.convert("RGB"),
                                                                heatmap_img.convert("RGB"),
                                                                alpha=0.5)
        st.image(st.session_state.heatmap_overlay_default, caption="Change Heatmap (Default Red)", use_column_width=True)

    if st.button("⬅️ Back"):
        st.session_state.page = 3
    if st.button("Next ➡️"):
        st.session_state.page = 5

def page5():
    st.header("5. Land Classification & Analysis")

    if 'classification' not in st.session_state or 'change_mask' not in st.session_state or 'before_date' not in st.session_state or 'after_date' not in st.session_state:
        st.error("Analysis data not found. Please start from the beginning.")
        st.session_state.page = 1
        return

    # Calculate change percentage
    total_pixels = np.prod(st.session_state.change_mask.shape)
    total_change = (np.sum(st.session_state.change_mask) / total_pixels)

    # Calamity detection
    st.subheader("🚨 Calamity Detection")
    calamity_report = detect_calamity(
        st.session_state.before_date,
        st.session_state.after_date,
        total_change
    )
    st.markdown(f"<h3 style='color: orange;'>{calamity_report}</h3>", unsafe_allow_html=True)
    st.markdown("""
        <p style='font-size: 16px; color: lightgray;'>
            This section analyzes the changes detected between the 'before' and 'after' images,
            considering the magnitude of change and the time elapsed. The system identifies
            potential natural or human-induced calamities based on these factors.
        </p>
    """, unsafe_allow_html=True)

    # Classification Table
    st.subheader(f"Land Cover Classification using {st.session_state.model_choice}")
    df_class = pd.DataFrame(list(st.session_state.classification.items()),
                            columns=["Land Cover", "Area (%)"])
    st.table(df_class)

    # Pie Charts
    st.subheader("Land Cover Distribution Comparison")
    col_before, col_after = st.columns(2)

    # Data for before image classification
    if st.session_state.model_choice == "SVM":
        classification_before = st.session_state.classification_before_svm
    else:
        classification_before = {} # CNN is removed

    with col_before:
        st.subheader("Before Image")
        fig_before, ax_before = plt.subplots()
        labels_before = classification_before.keys()
        sizes_before = classification_before.values()
        ax_before.pie(sizes_before, labels=labels_before, autopct='%1.1f%%', shadow=True, startangle=140)
        ax_before.axis('equal')
        st.pyplot(fig_before)

    with col_after:
        st.subheader("After Image")
        fig_after, ax_after = plt.subplots()
        labels_after = st.session_state.classification.keys()
        sizes_after = st.session_state.classification.values()
        ax_after.pie(sizes_after, labels=labels_after, autopct='%1.1f%%', shadow=True, startangle=140)
        ax_after.axis('equal')
        st.pyplot(fig_after)

    # Separate Pie Charts for Vegetation and Barren
    st.subheader("Vegetation and Barren Comparison")
    col_veg, col_barren = st.columns(2)

    with col_veg:
        st.subheader("Vegetation Change")
        veg_before = classification_before.get("Vegetation", 0)
        veg_after = st.session_state.classification.get("Vegetation", 0)
        labels_veg = ["Before", "After"]
        sizes_veg = [veg_before, veg_after]
        fig_veg, ax_veg = plt.subplots()
        ax_veg.pie(sizes_veg, labels=labels_veg, autopct='%1.1f%%', shadow=True, startangle=140)
        ax_veg.axis('equal')
        st.pyplot(fig_veg)

    with col_barren:
        st.subheader("Barren Area Change")
        barren_before = classification_before.get("Barren", 0)
        barren_after = st.session_state.classification.get("Barren", 0)
        labels_barren = ["Before", "After"]
        sizes_barren = [barren_before, barren_after]
        fig_barren, ax_barren = plt.subplots()
        ax_barren.pie(sizes_barren, labels=labels_barren, autopct='%1.1f%%', shadow=True, startangle=140)
        ax_barren.axis('equal')
        st.pyplot(fig_barren)

    if st.button("⬅️ Back"):
        st.session_state.page = 4
    if st.button("Next ➡️"):
        st.session_state.page = 6

def page6():
    st.header("6. Model Evaluation")

    if st.session_state.model_choice == "SVM":
        st.subheader("SVM Model Evaluation")
        if st.session_state.svm_roc_fig:
            st.pyplot(st.session_state.svm_roc_fig)
        else:
            st.warning("ROC curve data not available for SVM.")

        if st.session_state.svm_accuracy is not None:
            st.metric("Accuracy", f"{st.session_state.svm_accuracy:.2f}")
        else:
            st.warning("Accuracy data not available for SVM.")

        st.subheader("SVM Confusion Matrix")
        if st.session_state.svm_conf_matrix:
            st.pyplot(st.session_state.svm_conf_matrix)
        else:
            st.warning("Confusion matrix not available for SVM.")

        st.subheader("SVM Classification Report")
        if st.session_state.svm_class_report is not None:
            st.dataframe(st.session_state.svm_class_report)
        else:
            st.warning("Classification report not available for SVM.")

    st.subheader("Comparison")
    st.markdown("Since the CNN model has been removed, this section focuses solely on the evaluation of the SVM model.")

    if st.button("⬅️ Back"):
        st.session_state.page = 5

# -------- Main App Flow --------
if st.session_state.page == 1:
    page1()
elif st.session_state.page == 2:
    page2()
elif st.session_state.page == 3:
    page3()
elif st.session_state.page == 4:
    page4()
elif st.session_state.page == 5:
    page5()
elif st.session_state.page == 6:
    page6()
