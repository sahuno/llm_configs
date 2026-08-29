# ---------------------------------------------------------------------------
# 02_plot_cohort_heatmap.R
# Author : Samuel Ahuno (ekwame001@gmail.com)
# Date   : 2026-04-13
# Purpose: Recreate a SPECTRUM-style cohort data-availability heatmap from
#          a WIDE TSV (one row per sample, one column per assay).
#
# Input  : wide TSV (see 01_generate_mock_cohort.R); path via --input
# Output : <outdir>/{pdf,png,svg}/<name>.{pdf,png,svg}
#
# Usage (examples):
#   Rscript scripts/02_plot_cohort_heatmap.R --input data/cohort_wide.tsv
#   Rscript scripts/02_plot_cohort_heatmap.R \
#     -i data/cohort_wide.tsv -o results -n cohort_v1 \
#     --width 16 --height 9 \
#     --assays "DLP,WGS,scRNA-seq" \
#     --sig-order "FBI,HRD,HRD-Del,HRD-Dup,TD,Undetermined,NA" \
#     --no-svg
#
# Logic:
#   - Validate patient-level annotation constancy (same signature/BRCA*/CCNE1
#     across every row of a patient_id).
#   - Assign each sample a per-patient slot index (ordered by site, sample_id).
#   - For each assay A build a (slot x patient) matrix with 3 visible states:
#       Yes -> black, No -> white, NA -> light grey
#     NA covers both "not attempted" (assay column was NA in the input) and
#     "no sample at this slot for this patient" (patient has fewer samples
#     than the tallest patient in the cohort).
#   - Stack assay matrices with row_split so each assay forms a labelled block.
# ---------------------------------------------------------------------------

suppressPackageStartupMessages({
  library(optparse)
  library(dplyr)
  library(tidyr)
  library(readr)
  library(ComplexHeatmap)
  library(circlize)
  library(grid)
})

# ---- CLI --------------------------------------------------------------------
option_list <- list(
  make_option(c("-i", "--input"), type = "character", default = NULL,
              help = "Wide TSV (one row per sample). [required]",
              metavar = "FILE"),
  make_option(c("-o", "--outdir"), type = "character", default = "results",
              help = "Output root directory (will get pdf/, png/, svg/ subdirs) [%default]",
              metavar = "DIR"),
  make_option(c("-n", "--name"), type = "character",
              default = "cohort_overview_heatmap",
              help = "File stem for output figures [%default]",
              metavar = "STEM"),
  make_option(c("-W", "--width"),  type = "double", default = 14,
              help = "Figure width  in inches [%default]"),
  make_option(c("-H", "--height"), type = "double", default = 8,
              help = "Figure height in inches [%default]"),
  make_option("--assays", type = "character",
              default = "DLP,ONT,WGS,mpIF,scATAC-seq,scRNA-seq,scRNAseqVDJ",
              help = "Comma-separated assay column names, in plot order [%default]",
              metavar = "CSV"),
  make_option("--patient-cols", type = "character",
              default = "signature,BRCA1,BRCA2,CCNE1",
              help = "Comma-separated patient-level annotation columns; first column is used to order patients [%default]",
              metavar = "CSV"),
  make_option("--sig-order", type = "character",
              default = "FBI,HRD,HRD-Del,HRD-Dup,TD,Undetermined,NA",
              help = "Factor order for the first patient-level column [%default]",
              metavar = "CSV"),
  make_option("--sample-id-col", type = "character", default = "sample_id",
              help = "Sample-id column [%default]"),
  make_option("--patient-id-col", type = "character", default = "patient_id",
              help = "Patient-id column [%default]"),
  make_option("--site-col", type = "character", default = "site",
              help = "Site column [%default]"),
  make_option("--yes-color", type = "character", default = "#000000",
              help = "Cell colour for Yes (hex or R colour name) [%default]",
              metavar = "COLOUR"),
  make_option("--no-color", type = "character", default = "#BDBDBD",
              help = "Cell colour for No (attempted, failed/negative) [%default]",
              metavar = "COLOUR"),
  make_option("--na-color", type = "character", default = "#FFFFFF",
              help = "Cell colour for NA / not attempted [%default]",
              metavar = "COLOUR"),
  make_option("--na-as-no", action = "store_true", default = FALSE,
              help = "Treat NA cells as No (collapses legend to Yes/No; --na-color is ignored)"),
  make_option("--no-png", action = "store_true", default = FALSE,
              help = "Skip PNG export"),
  make_option("--no-pdf", action = "store_true", default = FALSE,
              help = "Skip PDF export"),
  make_option("--no-svg", action = "store_true", default = FALSE,
              help = "Skip SVG export")
)
opt <- parse_args(OptionParser(
  usage       = "Rscript %prog --input <wide.tsv> [options]",
  option_list = option_list,
  description = "Render a SPECTRUM-style cohort data-availability heatmap from a wide TSV."
))

if (is.null(opt$input)) {
  stop("--input is required (path to wide TSV). See --help.")
}
if (!file.exists(opt$input)) {
  stop("Input TSV not found: ", opt$input)
}

split_csv <- function(x) trimws(strsplit(x, ",", fixed = TRUE)[[1]])
assays       <- split_csv(opt$assays)
patient_cols <- split_csv(opt[["patient-cols"]])
sig_order    <- split_csv(opt[["sig-order"]])
id_col_p     <- opt[["patient-id-col"]]
id_col_s     <- opt[["sample-id-col"]]
site_col     <- opt[["site-col"]]

# validate colour inputs up-front so user gets a clear error, not a stack trace
check_colour <- function(x, what) {
  ok <- tryCatch({ grDevices::col2rgb(x); TRUE },
                 error = function(e) FALSE)
  if (!ok) stop(what, ": not a valid R colour spec: ", x)
  x
}
yes_colour <- check_colour(opt[["yes-color"]], "--yes-color")
no_colour  <- check_colour(opt[["no-color"]],  "--no-color")
na_colour  <- check_colour(opt[["na-color"]],  "--na-color")
na_as_no   <- isTRUE(opt[["na-as-no"]])

# ---- fonts / devices --------------------------------------------------------
.has_svglite  <- requireNamespace("svglite",  quietly = TRUE)
.has_showtext <- requireNamespace("showtext", quietly = TRUE)
if (.has_showtext) {
  showtext::showtext_auto()
  tryCatch(sysfonts::font_add("Arial",
           regular = "/System/Library/Fonts/Supplemental/Arial.ttf"),
           error = function(e) NULL)
  .fam <- "Arial"
} else {
  .fam <- "sans"
}

# ---- paths ------------------------------------------------------------------
res_dir <- normalizePath(opt$outdir, mustWork = FALSE)
for (d in file.path(res_dir, c("pdf", "png", "svg"))) {
  dir.create(d, showWarnings = FALSE, recursive = TRUE)
}

# ---- load & validate --------------------------------------------------------
wide <- read_tsv(opt$input, na = c("NA", ""), show_col_types = FALSE)

req_cols <- c(id_col_p, id_col_s, site_col, patient_cols, assays)
missing_cols <- setdiff(req_cols, colnames(wide))
if (length(missing_cols)) {
  stop("Input TSV missing columns: ", paste(missing_cols, collapse = ", "))
}

# normalize internal names so the rest of the script can use familiar identifiers
wide <- wide %>%
  rename(patient_id = !!id_col_p,
         sample_id  = !!id_col_s,
         site       = !!site_col)

# patient-level columns must be constant within patient_id
bad <- wide %>%
  group_by(patient_id) %>%
  summarise(across(all_of(patient_cols), ~ n_distinct(., na.rm = FALSE)), .groups = "drop") %>%
  filter(if_any(all_of(patient_cols), ~ . > 1))
if (nrow(bad)) {
  stop("Patient-level annotations vary within patient_id for: ",
       paste(bad$patient_id, collapse = ", "))
}

# ---- patient annotation (one row per patient) ------------------------------
# first patient-level column drives the column ordering (expected: Signature)
order_col <- patient_cols[1]
patient_anno <- wide %>%
  distinct(patient_id, !!!syms(patient_cols)) %>%
  mutate(!!order_col := factor(.data[[order_col]], levels = sig_order)) %>%
  arrange(.data[[order_col]], patient_id)

patient_order <- patient_anno$patient_id

# ---- assign per-patient sample slot ----------------------------------------
samples <- wide %>%
  arrange(patient_id, site, sample_id) %>%
  group_by(patient_id) %>%
  mutate(slot = row_number()) %>%
  ungroup()

max_slot <- max(samples$slot)

# ---- build matrices ---------------------------------------------------------
# presence_mat: (assay x slot) rows  by  patient cols
#   values in {"Yes","No","NA"} — "NA" is a string used as a categorical label
# site_mat   : same shape, holds the site label (or NA) of the sample at that slot
presence_list <- list()
site_list     <- list()

for (a in assays) {
  mat_p <- matrix("NA", nrow = max_slot, ncol = length(patient_order),
                  dimnames = list(paste(a, seq_len(max_slot), sep = "|"),
                                  patient_order))
  mat_s <- matrix(NA_character_, nrow = max_slot, ncol = length(patient_order),
                  dimnames = dimnames(mat_p))
  sub <- samples %>% select(patient_id, slot, site, value = all_of(a))
  for (i in seq_len(nrow(sub))) {
    rn <- paste(a, sub$slot[i], sep = "|")
    cn <- sub$patient_id[i]
    v  <- sub$value[i]
    mat_p[rn, cn] <- if (is.na(v)) "NA" else v
    mat_s[rn, cn] <- sub$site[i]
  }
  presence_list[[a]] <- mat_p
  site_list[[a]]     <- mat_s
}

presence_mat <- do.call(rbind, presence_list)
site_mat     <- do.call(rbind, site_list)

row_assay <- sub("\\|.*$", "", rownames(presence_mat))
row_assay <- factor(row_assay, levels = assays)

# representative site per row (most common across patients that have a sample there)
row_site <- apply(site_mat, 1, function(x) {
  x <- x[!is.na(x)]
  if (length(x) == 0) "Unknown" else names(sort(table(x), decreasing = TRUE))[1]
})

# ---- colour palettes --------------------------------------------------------
sig_cols <- c(
  "FBI"          = "#7A3B2E",
  "HRD"          = "#2E8B7A",
  "HRD-Del"      = "#4FA36D",
  "HRD-Dup"      = "#9BD3C0",
  "TD"           = "#D94A3D",
  "Undetermined" = "#8E8E8E",
  "NA"           = "#CFCFCF"
)
brca_cols  <- c("Absent" = "#FFFFFF", "Present" = "#000000", "Unknown" = "#BFBFBF")
ccne1_cols <- c("Amplified" = "#E41A1C", "Not Amplified" = "#D9D9D9")

site_cols <- c(
  "Adnexa"         = "#E41A1C",
  "Ascites"        = "#FF7F00",
  "Bowel"          = "#FFD92F",
  "Normal"         = "#4DAF4A",
  "Omentum"        = "#377EB8",
  "Other"          = "#984EA3",
  "Peritoneum"     = "#A6761D",
  "Unknown"        = "#7F7F7F",
  "Upper Quadrant" = "#66C2A5"
)

if (na_as_no) {
  presence_mat[presence_mat == "NA"] <- "No"
  presence_cols    <- c("Yes" = yes_colour, "No" = no_colour)
  legend_at        <- c("Yes", "No")
  legend_labels    <- c("Yes", "No")
} else {
  presence_cols    <- c("Yes" = yes_colour, "No" = no_colour, "NA" = na_colour)
  legend_at        <- c("Yes", "No", "NA")
  legend_labels    <- c("Yes", "No", "NA (not available)")
}

# ---- annotations ------------------------------------------------------------
# Build top annotation from --patient-cols. For common SPECTRUM columns
# (signature, BRCA1/2, CCNE1) known palettes are used; others get auto palettes.
known_palettes <- list(
  signature = sig_cols,
  BRCA1     = brca_cols,
  BRCA2     = brca_cols,
  CCNE1     = ccne1_cols
)
auto_palette <- function(vals) {
  lv <- sort(unique(vals[!is.na(vals)]))
  if (length(lv) == 0) return(character(0))
  pal <- if (requireNamespace("RColorBrewer", quietly = TRUE)) {
    RColorBrewer::brewer.pal(max(3, min(length(lv), 8)), "Set2")
  } else {
    grDevices::hcl.colors(length(lv), palette = "Dark 3")
  }
  setNames(pal[seq_along(lv)], lv)
}
anno_args <- setNames(
  lapply(patient_cols, function(cc) patient_anno[[cc]]),
  patient_cols
)
anno_cols_map <- setNames(
  lapply(patient_cols, function(cc) {
    if (!is.null(known_palettes[[cc]])) known_palettes[[cc]]
    else auto_palette(as.character(patient_anno[[cc]]))
  }),
  patient_cols
)

top_anno <- do.call(HeatmapAnnotation, c(
  anno_args,
  list(
    col = anno_cols_map,
    annotation_name_side = "right",
    annotation_name_gp   = gpar(fontsize = 10, fontfamily = .fam),
    simple_anno_size     = unit(4, "mm"),
    border               = TRUE,
    gap                  = unit(0.5, "mm")
  )
))

left_anno <- rowAnnotation(
  Site = row_site,
  col  = list(Site = site_cols),
  show_annotation_name = FALSE,
  simple_anno_size     = unit(3, "mm"),
  border               = TRUE
)

# ---- heatmap ----------------------------------------------------------------
ht <- Heatmap(
  presence_mat[, patient_order, drop = FALSE],
  name             = "Data",
  col              = presence_cols,
  rect_gp          = gpar(col = "grey85", lwd = 0.4),
  cluster_rows     = FALSE,
  cluster_columns  = FALSE,
  show_row_names   = FALSE,
  show_column_names = TRUE,
  column_names_gp  = gpar(fontsize = 6, fontfamily = .fam),
  column_names_rot = 90,
  row_split        = row_assay,
  row_title_rot    = 0,
  row_title_gp     = gpar(fontsize = 11, fontface = "bold", fontfamily = .fam),
  row_gap          = unit(1.2, "mm"),
  column_gap       = unit(0, "mm"),
  top_annotation   = top_anno,
  left_annotation  = left_anno,
  heatmap_legend_param = list(
    title     = "Data",
    at        = legend_at,
    labels    = legend_labels,
    title_gp  = gpar(fontsize = 10, fontface = "bold", fontfamily = .fam),
    labels_gp = gpar(fontsize = 9,  fontfamily = .fam)
  ),
  border     = TRUE,
  use_raster = FALSE
)

draw_heatmap <- function() {
  draw(ht,
       merge_legends          = TRUE,
       heatmap_legend_side    = "right",
       annotation_legend_side = "right")
}

# ---- export ----------------------------------------------------------------
w_in <- opt$width
h_in <- opt$height
stem <- opt$name

# macOS: `capabilities("cairo")` reports TRUE but cairo.so dynamically links
# against X11 which is usually missing — so prefer quartz there.
is_macos <- Sys.info()[["sysname"]] == "Darwin"
png_type <- if (is_macos && capabilities("aqua")) {
  "quartz"
} else if (capabilities("cairo")) {
  "cairo"
} else {
  "Xlib"
}

written <- character(0)

if (!opt[["no-png"]]) {
  p <- file.path(res_dir, "png", paste0(stem, ".png"))
  png(p, width = w_in, height = h_in, units = "in", res = 600, type = png_type)
  draw_heatmap(); dev.off()
  written <- c(written, p)
}

if (!opt[["no-pdf"]]) {
  p <- file.path(res_dir, "pdf", paste0(stem, ".pdf"))
  pdf(p, width = w_in, height = h_in)
  draw_heatmap(); dev.off()
  written <- c(written, p)
}

if (!opt[["no-svg"]]) {
  p <- file.path(res_dir, "svg", paste0(stem, ".svg"))
  if (.has_svglite) {
    svglite::svglite(p, width = w_in, height = h_in)
    draw_heatmap(); dev.off()
    written <- c(written, p)
  } else {
    message("Note: install `svglite` for a true SVG export; skipping SVG.")
  }
}

message("Wrote:\n  ", paste(written, collapse = "\n  "))
