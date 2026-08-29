# ---------------------------------------------------------------------------
# 01_generate_mock_cohort.R
# Author : Samuel Ahuno (ekwame001@gmail.com)
# Date   : 2026-04-13
# Purpose: Generate a mock SPECTRUM-style cohort dataset in WIDE format.
#          One row per sample. A single sample can contribute to many assays
#          (e.g. right-ovary tumour sample profiled with DLP + WGS + scRNA-seq).
#          Patient-level annotations (signature, BRCA1/2, CCNE1) repeat across
#          all rows that share a patient_id.
#
# Output : data/cohort_wide.tsv
#
#   patient_id  sample_id  site   signature  BRCA1  BRCA2  CCNE1
#     + one column per assay: DLP | ONT | WGS | mpIF | scATAC-seq
#                             scRNA-seq | scRNAseqVDJ
#   Assay cell values: "Yes" | "No" | NA   (NA = not attempted / unknown)
# ---------------------------------------------------------------------------

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(readr)
})

set.seed(42)

script_path <- sub("^--file=", "",
                   grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE))
proj_dir <- if (length(script_path) > 0) {
  dirname(dirname(normalizePath(script_path)))
} else {
  getwd()
}
out_dir <- file.path(proj_dir, "data")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

# ---- patient-level annotations ---------------------------------------------
n_patients <- 85
patient_id <- sprintf("%03d", sort(sample(1:220, n_patients)))

sig_levels <- c("FBI", "HRD", "HRD-Del", "HRD-Dup", "TD", "Undetermined", "NA")
sig_probs  <- c(0.22, 0.10, 0.12, 0.06, 0.18, 0.22, 0.10)

patient_anno <- tibble(
  patient_id = patient_id,
  signature  = sample(sig_levels, n_patients, TRUE, sig_probs),
  BRCA1      = sample(c("Present", "Absent", "Unknown"), n_patients, TRUE, c(0.80, 0.12, 0.08)),
  BRCA2      = sample(c("Present", "Absent", "Unknown"), n_patients, TRUE, c(0.82, 0.10, 0.08)),
  CCNE1      = sample(c("Not Amplified", "Amplified"),  n_patients, TRUE, c(0.82, 0.18))
) %>%
  mutate(
    CCNE1 = ifelse(signature == "FBI" & runif(n()) < 0.55, "Amplified", CCNE1),
    BRCA1 = ifelse(signature %in% c("HRD", "HRD-Del", "HRD-Dup") & runif(n()) < 0.35, "Absent", BRCA1),
    BRCA2 = ifelse(signature %in% c("HRD", "HRD-Del", "HRD-Dup") & runif(n()) < 0.25, "Absent", BRCA2)
  )

# ---- per-sample rows --------------------------------------------------------
sites <- c("Adnexa", "Ascites", "Bowel", "Normal", "Omentum",
           "Other", "Peritoneum", "Unknown", "Upper Quadrant")
site_probs <- c(0.18, 0.10, 0.08, 0.10, 0.18, 0.06, 0.12, 0.10, 0.08)

assays <- c("DLP", "ONT", "WGS", "mpIF", "scATAC-seq", "scRNA-seq", "scRNAseqVDJ")

# probability a given sample was attempted for each assay
p_attempt <- c(
  "DLP" = 0.45, "ONT" = 0.25, "WGS" = 0.60, "mpIF" = 0.35,
  "scATAC-seq" = 0.25, "scRNA-seq" = 0.40, "scRNAseqVDJ" = 0.30
)
# probability of Yes (vs No) given attempted
p_yes <- c(
  "DLP" = 0.85, "ONT" = 0.75, "WGS" = 0.95, "mpIF" = 0.80,
  "scATAC-seq" = 0.70, "scRNA-seq" = 0.85, "scRNAseqVDJ" = 0.75
)

# how many samples per patient (1..8)
n_sample_dist <- c(0.15, 0.22, 0.22, 0.16, 0.12, 0.07, 0.04, 0.02)

sample_rows <- list()
for (pid in patient_id) {
  n_samples <- sample(1:8, 1, prob = n_sample_dist)
  for (s in seq_len(n_samples)) {
    row <- list(
      patient_id = pid,
      sample_id  = sprintf("%s_S%02d", pid, s),
      site       = sample(sites, 1, prob = site_probs)
    )
    for (a in assays) {
      attempted <- rbinom(1, 1, p_attempt[[a]]) == 1
      row[[a]] <- if (!attempted) NA_character_ else
        ifelse(rbinom(1, 1, p_yes[[a]]) == 1, "Yes", "No")
    }
    sample_rows[[length(sample_rows) + 1]] <- as_tibble(row)
  }
}
samples <- bind_rows(sample_rows)

# ---- merge patient-level annotations (repeated across rows) ----------------
cohort_wide <- samples %>%
  left_join(patient_anno, by = "patient_id") %>%
  select(patient_id, sample_id, site,
         signature, BRCA1, BRCA2, CCNE1,
         all_of(assays))

write_tsv(cohort_wide, file.path(out_dir, "cohort_wide.tsv"), na = "NA")

message("Wrote: ", file.path(out_dir, "cohort_wide.tsv"))
message("  patients : ", n_distinct(cohort_wide$patient_id))
message("  samples  : ", nrow(cohort_wide))
message("  assays   : ", paste(assays, collapse = ", "))
