#!/usr/bin/env Rscript
# sciAuditor R front-end (Layer A, static)
# Author: Samuel Ahuno / sciAuditor
# Date: 2026-05-14
# Purpose: Read an R analysis script and emit a v0.2 inferred YAML
#   (see sciAuditor/02_inference_design.md §4 for the schema).
#
# Scope (round 1): static AST walk only. Covers ~70% of the v0.2 schema
# blocks needed by ordinary tabular scripts: config_interface, inputs,
# outputs, side_effects, environment, compliance_checks,
# audit_findings_preview, plus a coarse dataframes/transformations
# lineage. NOT yet implemented: package_resources (allowlist),
# functions_defined I/O propagation, models, figures, hardcoded_data
# kind taxonomy, runtime trace, LLM assist.

suppressPackageStartupMessages({
  library(optparse)
  library(yaml)
})

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
option_list <- list(
  make_option(c("-i", "--input"),  type = "character",
              help = "R script to analyse [required]"),
  make_option(c("-o", "--output"), type = "character", default = "-",
              help = "output YAML path, '-' for stdout [default %default]"),
  make_option(c("--report_dir"), type = "character", default = NULL,
              help = "emit audit_report.md + audit_findings.tsv into this dir"),
  make_option(c("--pair_launcher"), type = "character", default = NULL,
              help = "bash launcher that invokes this R script; auditor will compose a pair_unit block by shelling out to parser_bash/sciauditor_bash.py"),
  make_option(c("--bash_parser"), type = "character", default = NULL,
              help = "path to sciauditor_bash.py [default: ../parser_bash/sciauditor_bash.py relative to this script]"),
  make_option(c("--analysis_unit_id"), type = "character", default = NULL,
              help = "override analysis_unit.id; defaults to basename of input"),
  make_option(c("--schema_version"), type = "character", default = "0.2",
              help = "[default %default]")
)
opt <- parse_args(OptionParser(option_list = option_list))
if (is.null(opt$input)) stop("must pass --input")
if (!file.exists(opt$input)) stop("input not found: ", opt$input)

# Resolve --bash_parser default relative to this script's location
resolve_bash_parser <- function(user_value) {
  if (!is.null(user_value)) return(normalizePath(user_value, mustWork = FALSE))
  # Find our own location via commandArgs
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- args[grep("^--file=", args)]
  script_path <- if (length(file_arg)) sub("^--file=", "", file_arg[1]) else NULL
  if (is.null(script_path)) return(NULL)
  script_dir <- dirname(normalizePath(script_path, mustWork = FALSE))
  file.path(script_dir, "..", "parser_bash", "sciauditor_bash.py")
}

# ---------------------------------------------------------------------------
# Casetrack append extractor — round-2 addition (symmetric with parser_py /
# parser_bash). Scans raw source for `casetrack ... append ...` regardless
# of how it's invoked (system(), system2(), processx::run, glue() into
# system, etc.) — the literal tokens 'casetrack' and 'append' appear in
# every form. Same regex shape as the Python/bash extractors so
# casetrack_check.py consumes the YAML field identically across languages.
# ---------------------------------------------------------------------------
# Round-2: widened delimiter to [\\s\\S]{1,40} for symmetry with parser_py /
# parser_bash (catches forms like system2("casetrack", c("append",...))).
CASETRACK_APPEND_RE <- "(?i)\\bcasetrack\\b[\\s\\S]{1,40}?\\bappend\\b[\\s\\S]{0,500}?(?:\\n\\n|$|;;)"
CT_ANALYSIS_RE    <- "--analysis[=\\s,\"'\\]]+([^\\s'\",)\\]]+)"
CT_RESULTS_RE     <- "--results[=\\s,\"'\\]]+([^\\s'\",)\\]]+)"
CT_PROJECT_DIR_RE <- "--project[_-]dir[=\\s,\"'\\]]+([^\\s'\",)\\]]+)"

extract_casetrack_appends <- function(source_text) {
  out <- list()
  if (!nzchar(source_text)) return(out)
  m <- gregexpr(CASETRACK_APPEND_RE, source_text, perl = TRUE)[[1]]
  if (length(m) == 1L && m[[1]] == -1L) return(out)
  match_lens <- attr(m, "match.length")
  for (i in seq_along(m)) {
    start_pos <- m[[i]]; len <- match_lens[[i]]
    block <- substr(source_text, start_pos, start_pos + len - 1L)
    am <- regmatches(block, regexec(CT_ANALYSIS_RE, block, perl = TRUE))[[1]]
    rm <- regmatches(block, regexec(CT_RESULTS_RE,  block, perl = TRUE))[[1]]
    pm <- regmatches(block, regexec(CT_PROJECT_DIR_RE, block, perl = TRUE))[[1]]
    if (length(am) < 2L && length(rm) < 2L) next  # skip blocks with no flags
    prefix <- substr(source_text, 1L, start_pos - 1L)
    site   <- length(strsplit(prefix, "\n", fixed = TRUE)[[1]]) + 1L
    out[[length(out) + 1L]] <- list(
      analysis    = if (length(am) > 1L) am[[2L]] else NA_character_,
      results     = if (length(rm) > 1L) rm[[2L]] else NA_character_,
      project_dir = if (length(pm) > 1L) pm[[2L]] else NA_character_,
      site        = as.integer(site)
    )
  }
  out
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
`%||%` <- function(a, b) if (!is.null(a)) a else b

# Get the canonical name of the called function, including pkg::fn form
call_name <- function(e) {
  if (!is.call(e)) return(NA_character_)
  fn <- e[[1]]
  if (is.name(fn)) return(as.character(fn))
  if (is.call(fn) && length(fn) == 3 && identical(fn[[1]], as.name("::"))) {
    return(paste0(as.character(fn[[2]]), "::", as.character(fn[[3]])))
  }
  NA_character_
}

# Best-effort extraction of (start_line, end_line) from any srcref attribute.
srcref_lines <- function(e) {
  sr <- attr(e, "srcref")
  if (is.null(sr)) return(c(NA_integer_, NA_integer_))
  if (is.list(sr) && length(sr) >= 1 && !is.null(sr[[1]]) && length(sr[[1]]) >= 4) {
    return(c(sr[[1]][1], sr[[length(sr)]][3]))
  }
  if (is.integer(sr) && length(sr) >= 4) return(c(sr[1], sr[3]))
  if (is.numeric(sr) && length(sr) >= 4) return(c(as.integer(sr[1]), as.integer(sr[3])))
  c(NA_integer_, NA_integer_)
}

# Build a per-call-name FIFO of call-site line numbers from getParseData.
# Indexes both `SYMBOL_FUNCTION_CALL` (regular calls) and assignment
# operators (LEFT_ASSIGN, EQ_ASSIGN, RIGHT_ASSIGN), so assignments —
# which `walk_collect` encounters as calls to "<-" / "=" / "->" —
# also get line numbers when their srcref attribute is dropped.
build_call_line_map <- function(parse_tree) {
  pd <- utils::getParseData(parse_tree)
  out <- new.env(parent = emptyenv())
  if (is.null(pd) || nrow(pd) == 0) return(out)
  rows <- pd[pd$token %in% c("SYMBOL_FUNCTION_CALL", "LEFT_ASSIGN",
                             "EQ_ASSIGN", "RIGHT_ASSIGN"),
             c("line1","text"), drop = FALSE]
  rows <- rows[order(rows$line1), ]
  for (i in seq_len(nrow(rows))) {
    nm <- rows$text[i]
    out[[nm]] <- c(out[[nm]] %||% integer(0), rows$line1[i])
  }
  out
}

# Pop the next line for `fn_name` off the map (FIFO so source order matches
# walk order for top-down traversal of the AST).
pop_call_line <- function(map, fn_name) {
  if (is.null(fn_name) || is.na(fn_name) || is.null(map[[fn_name]]) ||
      length(map[[fn_name]]) == 0) {
    return(NA_integer_)
  }
  v <- map[[fn_name]]
  map[[fn_name]] <- v[-1]
  v[1]
}

# Recursively collect every call expression with its source line range.
# Lines come from srcref when present; otherwise from the parse-data map by
# function name in source order.
walk_collect <- function(top, line_map) {
  out <- list()
  rec <- function(e, parent_lines) {
    if (is.call(e)) {
      lines <- srcref_lines(e)
      if (any(is.na(lines))) {
        # Fall back to the parse-data map: pop the next line for this fn name
        fn_name_simple <- tryCatch({
          fn <- e[[1]]
          if (is.name(fn)) as.character(fn)
          else if (is.call(fn) && length(fn) == 3 &&
                   identical(fn[[1]], as.name("::"))) as.character(fn[[3]])
          else NA_character_
        }, error = function(...) NA_character_)
        from_map <- pop_call_line(line_map, fn_name_simple)
        if (!is.na(from_map)) lines <- c(from_map, from_map)
        else if (!any(is.na(parent_lines))) lines <- parent_lines
      }
      out[[length(out) + 1]] <<- list(call = e,
                                      line_start = lines[1],
                                      line_end   = lines[2])
      for (i in seq_along(e)) rec(e[[i]], lines)
    } else if (is.expression(e)) {
      for (i in seq_along(e)) rec(e[[i]], parent_lines)
    }
  }
  init <- c(NA_integer_, NA_integer_)
  if (is.expression(top)) {
    for (i in seq_along(top)) rec(top[[i]], srcref_lines(top[[i]]))
  } else rec(top, init)
  out
}

# Map: variable name -> literal value, from simple `name <- "literal"` assigns
collect_simple_assigns <- function(top) {
  out <- list()
  walk_assigns <- function(e) {
    if (is.call(e) && length(e) == 3 &&
        (identical(e[[1]], as.name("<-")) || identical(e[[1]], as.name("=")))) {
      lhs <- e[[2]]; rhs <- e[[3]]
      if (is.name(lhs) && (is.character(rhs) || is.numeric(rhs) || is.logical(rhs)) &&
          length(rhs) == 1) {
        out[[as.character(lhs)]] <<- as.character(rhs)
      }
    }
    if (is.call(e) || is.expression(e)) for (i in seq_along(e)) walk_assigns(e[[i]])
  }
  if (is.expression(top)) for (i in seq_along(top)) walk_assigns(top[[i]])
  else walk_assigns(top)
  out
}

# Get an arg from a call by name; falls back to positional pos among unnamed
arg_by <- function(call, name = NULL, pos = NULL) {
  args <- as.list(call)[-1]
  nms  <- names(args) %||% rep("", length(args))
  if (!is.null(name) && nzchar(name) && name %in% nms) {
    return(args[[match(name, nms)]])
  }
  if (!is.null(pos)) {
    unnamed <- which(!nzchar(nms))
    if (length(unnamed) >= pos) return(args[[unnamed[pos]]])
  }
  NULL
}

# Single-line deparse (capped) for any expression
expr_text <- function(e, max_len = 200) {
  s <- paste(deparse(e, width.cutoff = 500L), collapse = " ")
  s <- gsub("\\s+", " ", s)
  if (nchar(s) > max_len) s <- paste0(substr(s, 1, max_len - 1), "...")
  s
}

# Render any arg as a path template + bindings
arg_to_path <- function(arg, assigns = list()) {
  if (is.null(arg)) return(list(template = NA_character_, confidence = "low"))
  if (is.character(arg) && length(arg) == 1) {
    return(list(template = arg, confidence = "high"))
  }
  if (is.name(arg)) {
    nm <- as.character(arg)
    lit <- assigns[[nm]]
    if (!is.null(lit)) return(list(template = lit, confidence = "high",
                                   note = paste0("resolved from `", nm, "` assign")))
    return(list(template = sprintf("{%s}", nm), confidence = "medium"))
  }
  if (is.call(arg) && length(arg) == 3 && identical(arg[[1]], as.name("$"))) {
    obj <- as.character(arg[[2]]); fld <- as.character(arg[[3]])
    return(list(template = sprintf("{%s.%s}", obj, fld), confidence = "high"))
  }
  if (is.call(arg) && length(arg) == 3 && identical(arg[[1]], as.name("[["))) {
    obj <- as.character(arg[[2]]); fld <- as.character(arg[[3]])
    return(list(template = sprintf("{%s.%s}", obj, fld), confidence = "high"))
  }
  if (is.call(arg) && identical(arg[[1]], as.name("file.path"))) {
    parts <- as.list(arg)[-1]
    txts <- vapply(parts, function(p) arg_to_path(p, assigns)$template, character(1))
    return(list(template = paste(txts, collapse = "/"), confidence = "medium"))
  }
  if (is.call(arg) && (identical(arg[[1]], as.name("paste0")) ||
                       identical(arg[[1]], as.name("paste")))) {
    parts <- as.list(arg)[-1]
    nms <- names(parts) %||% rep("", length(parts))
    pieces <- mapply(function(p, nm) if (identical(nm, "sep") || identical(nm, "collapse")) ""
                                     else arg_to_path(p, assigns)$template,
                     parts, nms, SIMPLIFY = TRUE)
    sep <- if (identical(arg[[1]], as.name("paste"))) {
      sep_a <- arg_by(arg, name = "sep"); if (is.character(sep_a)) sep_a else " "
    } else ""
    return(list(template = paste(pieces, collapse = sep), confidence = "medium"))
  }
  list(template = expr_text(arg), confidence = "low")
}

# ---------------------------------------------------------------------------
# Pattern catalogues
# ---------------------------------------------------------------------------
READ_FNS <- c("fread", "data.table::fread",
              "read.csv", "read.csv2", "read.delim", "read.delim2",
              "read.table", "read_tsv", "read_csv", "read_delim",
              "readr::read_tsv", "readr::read_csv", "readr::read_delim",
              "readRDS", "yaml::read_yaml", "yaml::yaml.load_file")
WRITE_FNS <- c("fwrite", "data.table::fwrite",
               "write.csv", "write.csv2", "write.table",
               "write_tsv", "write_csv",
               "readr::write_tsv", "readr::write_csv",
               "saveRDS", "ggsave")
MKDIR_FNS  <- c("dir.create", "fs::dir_create")
OPTION_FNS <- c("make_option", "optparse::make_option")
LIBRARY_FNS <- c("library", "require", "requireNamespace")

# Stochastic functions whose presence implies a seed should be set
STOCHASTIC_FNS <- c(
  "sample", "rnorm", "runif", "rbinom", "rpois", "kmeans", "Rtsne",
  "uwot::umap", "umap::umap", "ClusterProfiler::GSEA", "clusterProfiler::GSEA",
  "GSEA", "set.seed"  # set.seed itself is informative as the *setter*
)

# Forbidden variable names (CLAUDE.md)
FORBIDDEN_NAMES <- c("counts", "results", "mean", "median", "sum", "conditions")

# Tabular write extensions for "header preserved" check
TABULAR_EXTS <- c("tsv", "csv", "txt", "bed", "bedgraph", "bedmethyl")

# ---------------------------------------------------------------------------
# Collectors (one per top-level schema block)
# ---------------------------------------------------------------------------
collect_packages <- function(calls_all) {
  pkgs <- character()
  for (item in calls_all) {
    nm <- call_name(item$call)
    if (!is.na(nm) && nm %in% LIBRARY_FNS) {
      a <- as.list(item$call)[-1]
      if (length(a) >= 1) {
        v <- a[[1]]
        if (is.name(v)) pkgs <- c(pkgs, as.character(v))
        else if (is.character(v)) pkgs <- c(pkgs, v)
      }
    }
  }
  unique(pkgs)
}

collect_config_interface <- function(calls_all) {
  options_out <- list()
  for (item in calls_all) {
    if (!identical(call_name(item$call), "make_option") &&
        !identical(call_name(item$call), "optparse::make_option")) next
    names_arg <- arg_by(item$call, pos = 1)
    type_arg  <- arg_by(item$call, name = "type")
    def_arg   <- arg_by(item$call, name = "default")
    help_arg  <- arg_by(item$call, name = "help")

    flag_long <- NA_character_
    if (is.character(names_arg) && length(names_arg) == 1) {
      flag_long <- names_arg
    } else if (is.call(names_arg) && identical(names_arg[[1]], as.name("c"))) {
      flags <- unlist(lapply(as.list(names_arg)[-1],
                             function(x) if (is.character(x)) x else NA))
      long <- flags[grepl("^--", flags)]
      if (length(long)) flag_long <- long[1]
      else if (length(flags)) flag_long <- flags[1]
    }
    default_val <- if (is.null(def_arg)) NULL
                   else if (is.atomic(def_arg) && length(def_arg) == 1) def_arg
                   else expr_text(def_arg)
    default_kind <- NULL
    if (is.character(default_val) && length(default_val) == 1) {
      default_kind <- if (startsWith(default_val, "/")) "absolute" else "relative"
    }
    options_out[[length(options_out) + 1]] <- list(
      name         = flag_long,
      type         = if (!is.null(type_arg) && is.character(type_arg)) type_arg else NULL,
      default      = default_val,
      default_kind = default_kind,
      help         = if (!is.null(help_arg) && is.character(help_arg)) help_arg else NULL,
      site         = item$line_start
    )
  }
  list(framework = if (length(options_out)) "optparse" else "none",
       options   = options_out)
}

collect_inputs <- function(calls_all, assigns) {
  out <- list()
  for (item in calls_all) {
    nm <- call_name(item$call)
    if (is.na(nm) || !(nm %in% READ_FNS)) next
    p_arg <- arg_by(item$call, name = "file") %||%
             arg_by(item$call, name = "input") %||%
             arg_by(item$call, pos = 1)
    pr <- arg_to_path(p_arg, assigns)
    # Capture header-handling args so the header-preserved BLOCKER can
    # cite them at compliance time.
    header_arg    <- arg_by(item$call, name = "header")
    col_names_arg <- arg_by(item$call, name = "col.names")
    skip_arg      <- arg_by(item$call, name = "skip")
    header_dropped <- identical(header_arg, FALSE) ||
                      identical(col_names_arg, FALSE)
    # YAML can't serialise language objects; reduce each captured arg to
    # either an atomic length-1 value or a deparsed text fragment.
    yaml_safe <- function(a) {
      if (is.null(a)) return(NULL)
      if (is.atomic(a) && length(a) == 1) return(a)
      expr_text(a, 80)
    }
    out[[length(out) + 1]] <- list(
      id              = sprintf("input_%02d", length(out) + 1),
      path_template   = pr$template,
      kind            = "tabular",
      format          = guess_format_from_fn(nm, pr$template),
      read_call       = list(fn = nm, site = item$line_start),
      read_params     = list(
        header    = yaml_safe(header_arg),
        col.names = yaml_safe(col_names_arg),
        skip      = yaml_safe(skip_arg)
      ),
      header_dropped  = header_dropped,
      resolution_confidence = pr$confidence
    )
  }
  out
}

link_outputs_to_dataframes <- function(outputs, dataframes, calls_all) {
  # Round-2: set `written_by` on each output to the dataframe id whose
  # value is being written. For R's WRITE_FNS the data is always at
  # positional 1 (fwrite/write.csv/write.table/write_csv/write_tsv/saveRDS).
  # Falls back to nearest-preceding dataframe by line when pos1 isn't a
  # bare name. Returns the mutated outputs list.
  if (!length(outputs)) return(outputs)
  df_ids <- vapply(dataframes, function(d) d$id %||% NA_character_, character(1))
  df_sites <- vapply(dataframes, function(d) d$site %||% NA_integer_, integer(1))
  # Index calls_all by line for receiver lookup
  call_by_line <- list()
  for (item in calls_all) {
    call_by_line[[as.character(item$line_start)]] <- item$call
  }
  for (i in seq_along(outputs)) {
    o <- outputs[[i]]
    wc <- o$write_call %||% list()
    site <- wc$site %||% NA_integer_
    fn <- wc$fn %||% ""
    written_by <- NULL
    # Try pos-1 of the call at that line
    if (!is.na(site)) {
      this_call <- call_by_line[[as.character(site)]]
      if (!is.null(this_call) && is.call(this_call)) {
        first <- arg_by(this_call, pos = 1)
        if (is.name(first)) {
          cand <- as.character(first)
          if (cand %in% df_ids) written_by <- cand
        }
      }
    }
    # Fallback: nearest preceding dataframe within 30 lines
    if (is.null(written_by) && !is.na(site)) {
      cand_idx <- which(!is.na(df_sites) & df_sites <= site & (site - df_sites) <= 30)
      if (length(cand_idx)) {
        i_pick <- cand_idx[which.max(df_sites[cand_idx])]
        written_by <- df_ids[i_pick]
      }
    }
    outputs[[i]]$written_by <- if (is.null(written_by)) NA else written_by
  }
  outputs
}


collect_outputs <- function(calls_all, assigns) {
  out <- list()
  for (item in calls_all) {
    nm <- call_name(item$call)
    if (is.na(nm) || !(nm %in% WRITE_FNS)) next
    # For fwrite/readr::write_*: data is pos1, file is pos2 or named `file`
    # For write.csv/write.table: pos2 or named `file`
    p_arg <- arg_by(item$call, name = "file") %||%
             arg_by(item$call, name = "filename") %||%
             arg_by(item$call, pos = 2)
    pr <- arg_to_path(p_arg, assigns)
    sep_arg <- arg_by(item$call, name = "sep")
    col_names_arg <- arg_by(item$call, name = "col.names")
    header_arg <- arg_by(item$call, name = "header")
    write_mode <- if (identical(arg_by(item$call, name = "append"), TRUE)) "append" else "overwrite"
    write_params <- list()
    if (is.character(sep_arg)) write_params$sep <- sep_arg
    if (!is.null(col_names_arg)) write_params$col.names <- col_names_arg
    if (!is.null(header_arg))    write_params$header    <- header_arg

    out[[length(out) + 1]] <- list(
      id              = sprintf("output_%02d", length(out) + 1),
      kind            = "tabular",
      format          = guess_format_from_fn(nm, pr$template),
      path_template   = pr$template,
      write_call      = list(fn = nm, site = item$line_start),
      write_mode      = write_mode,
      write_params    = if (length(write_params)) write_params else NULL,
      resolution_confidence = pr$confidence
    )
  }
  out
}

guess_format_from_fn <- function(fn, path = NA_character_) {
  if (!is.na(path) && nzchar(path)) {
    ext <- tolower(sub(".*\\.", "", path))
    if (ext %in% c("tsv","csv","txt","bed","bedgraph","bedmethyl","rds")) return(ext)
  }
  if (grepl("(^|::)fread$|read\\.delim|read_tsv|write_tsv|fwrite$|write\\.table", fn)) return("tsv")
  if (grepl("read\\.csv|read_csv|write\\.csv|write_csv", fn)) return("csv")
  if (grepl("saveRDS|readRDS", fn)) return("rds")
  if (grepl("ggsave", fn)) return("multi")
  if (grepl("yaml", fn)) return("yaml")
  "unknown"
}

collect_side_effects <- function(calls_all) {
  out <- list()
  for (item in calls_all) {
    nm <- call_name(item$call)
    if (is.na(nm)) next
    if (nm %in% MKDIR_FNS) {
      pr <- arg_to_path(arg_by(item$call, pos = 1), list())
      out[[length(out) + 1]] <- list(site = item$line_start,
                                     kind = "mkdir",
                                     paths = list(pr$template))
    } else if (nm == "options") {
      out[[length(out) + 1]] <- list(site = item$line_start,
                                     kind = "r_option",
                                     detail = expr_text(item$call, 160))
    } else if (nm == "setwd") {
      out[[length(out) + 1]] <- list(site = item$line_start,
                                     kind = "setwd",
                                     detail = expr_text(item$call, 160))
    } else if (nm == "Sys.setenv") {
      out[[length(out) + 1]] <- list(site = item$line_start,
                                     kind = "env_set",
                                     detail = expr_text(item$call, 160))
    }
  }
  out
}

collect_stochastic_ops <- function(calls_all) {
  out <- list()
  # First pass: record (line, value) of every set.seed call
  seed_pairs <- list()
  for (item in calls_all) {
    if (identical(call_name(item$call), "set.seed")) {
      v <- arg_by(item$call, pos = 1)
      val <- if (is.numeric(v) && length(v) == 1) as.integer(v) else NA_integer_
      seed_pairs[[length(seed_pairs) + 1]] <- list(line = item$line_start, value = val)
    }
  }
  seed_sites <- vapply(seed_pairs, function(x) x$line, integer(1))
  # Second pass: linear-order "is there a set.seed earlier in the file?"
  for (item in calls_all) {
    nm <- call_name(item$call)
    if (is.na(nm) || nm == "set.seed") next
    if (!(nm %in% STOCHASTIC_FNS)) next
    earlier <- which(seed_sites <= item$line_start)
    out[[length(out) + 1]] <- list(
      site     = item$line_start,
      fn       = nm,
      seed_set = length(earlier) > 0,
      seed_set_evidence_site = if (length(earlier)) seed_sites[max(earlier)] else NA_integer_,
      seed_value = if (length(earlier)) seed_pairs[[max(earlier)]]$value else NA_integer_
    )
  }
  out
}

# ---------------------------------------------------------------------------
# Phase 1.5 collectors: hardcoded_data, dataframes, models
# ---------------------------------------------------------------------------
HARDCODED_MIN_LITERALS <- 5L

site_str <- function(start, end) {
  if (is.na(start)) return(NA_character_)
  if (is.na(end) || identical(start, end)) return(as.character(start))
  sprintf("%d-%d", start, end)
}

# Extract every Name node inside an expression (recursive). Used to find which
# previously-seen dataframe ids are referenced as inputs to a call.
extract_name_refs <- function(e) {
  if (is.name(e)) return(as.character(e))
  if (is.call(e)) {
    refs <- character()
    for (i in seq_along(e)) refs <- c(refs, extract_name_refs(e[[i]]))
    return(refs)
  }
  character()
}

# Scan ~10 lines before `line_start` for PMID / DOI citations.
# Two-pass per line: (1) any line mentioning PMID / PMIDs / PubMed contributes
# every ≥6-digit integer as a PMID; (2) DOI patterns extracted directly.
# Catches comma-separated PMID lists like "PMIDs 25422890, 40439998, ...".
extract_citations_near <- function(line_start, raw_lines, lookback = 10L) {
  if (is.na(line_start) || line_start <= 1) return(character())
  s <- max(1L, line_start - lookback)
  block <- raw_lines[s:(line_start - 1)]
  hits <- character()
  for (line in block) {
    if (grepl("\\bPMID|pubmed", line, ignore.case = TRUE, perl = TRUE)) {
      ids <- unlist(regmatches(line, gregexpr("\\d{6,}", line)))
      if (length(ids)) hits <- c(hits, paste0("PMID:", ids))
    }
    dois <- unlist(regmatches(line, gregexpr("10\\.\\d+/[^\\s,;]+", line)))
    if (length(dois)) hits <- c(hits, paste0("DOI:", dois))
  }
  unique(hits)
}

classify_string_set <- function(values) {
  # Order matters: most specific first.
  # 1) Contig names
  if (all(grepl("^chr[0-9XYM]+$|^[1-9][0-9]*$|^[XYMT]+$", values))) return("contig_list")
  # 2) Sample IDs: separator-bearing (hyphen or dot), typical of cohort IDs
  #    (e.g. SU2C-264, p17424_3, R.S.2). Must beat gene-symbol classifier.
  if (mean(grepl("[.-]|_", values)) >= 0.6 && any(grepl("[0-9]", values))) {
    return("sample_id_list")
  }
  # 3) Gene symbols: 2-12 chars, letter-start, alphanum + . / -
  gene_like <- grepl("^[A-Za-z][A-Za-z0-9.-]{1,11}$", values)
  if (mean(gene_like) >= 0.85) return("curated_geneset")
  "string_list"
}

classify_hardcoded <- function(name, rhs, line_start, line_end, raw_lines) {
  # `c("a","b",...)` with ≥5 char literals
  if (is.call(rhs) && identical(rhs[[1]], as.name("c"))) {
    args <- as.list(rhs)[-1]
    char_args <- Filter(function(x) is.character(x) && length(x) == 1 && !is.na(x), args)
    if (length(char_args) >= HARDCODED_MIN_LITERALS) {
      values <- unlist(char_args)
      cits <- extract_citations_near(line_start, raw_lines)
      return(list(
        id        = name,
        site      = site_str(line_start, line_end),
        kind      = classify_string_set(values),
        count     = as.integer(length(values)),
        values    = if (length(values) <= 20L) as.list(values) else NULL,
        citations = if (length(cits)) as.list(cits) else NULL
      ))
    }
  }
  # `list(name=c(...), name=c(...), ...)` — structured curated set
  if (is.call(rhs) && identical(rhs[[1]], as.name("list"))) {
    sub_lists <- as.list(rhs)[-1]
    nms <- names(sub_lists) %||% rep("", length(sub_lists))
    sub_counts <- vapply(sub_lists, function(s) {
      if (is.call(s) && identical(s[[1]], as.name("c"))) {
        sum(vapply(as.list(s)[-1], function(x) is.character(x) && length(x) == 1, logical(1)))
      } else 0L
    }, integer(1))
    total <- as.integer(sum(sub_counts))
    nonempty <- as.integer(sum(sub_counts > 0))
    if (total >= HARDCODED_MIN_LITERALS && nonempty >= 2L) {
      cits <- extract_citations_near(line_start, raw_lines)
      return(list(
        id              = name,
        site            = site_str(line_start, line_end),
        kind            = "curated_geneset_structured",
        count           = total,
        sub_categories  = nonempty,
        sub_category_names = as.list(nms[nzchar(nms)]),
        citations       = if (length(cits)) as.list(cits) else NULL
      ))
    }
  }
  NULL
}

# Walk every <- / = binding via the pre-resolved calls_all list (which has
# stable line numbers from the parse-data map). Filtering inside calls_all
# is cleaner than re-recursing the parse tree and re-handling srcrefs.
collect_hardcoded_data <- function(calls_all, raw_lines) {
  out <- list()
  for (item in calls_all) {
    e <- item$call
    if (!(is.call(e) && length(e) == 3 &&
          (identical(e[[1]], as.name("<-")) || identical(e[[1]], as.name("="))))) next
    lhs <- e[[2]]; rhs <- e[[3]]
    if (!is.name(lhs)) next
    entry <- classify_hardcoded(as.character(lhs), rhs,
                                item$line_start, item$line_end, raw_lines)
    if (!is.null(entry)) out[[length(out) + 1]] <- entry
  }
  out
}

# Classify the RHS of a binding as a dataframe operation.
df_classify <- function(rhs, known_frames) {
  if (!is.call(rhs)) return(NULL)
  fn <- call_name(rhs)
  # Pipe expression: a %>% b %>% c
  if (length(rhs) == 3 &&
      (identical(rhs[[1]], as.name("%>%")) || identical(rhs[[1]], as.name("|>")))) {
    refs <- intersect(extract_name_refs(rhs), known_frames)
    if (length(refs)) {
      return(list(derived_from = as.list(unique(refs)),
                  transform = list(op = "pipe", expr = expr_text(rhs, 200))))
    }
  }
  # `df[predicate, ]` or `df[, cols]` — both base R and data.table subset
  if (length(rhs) >= 2 && identical(rhs[[1]], as.name("["))) {
    base <- rhs[[2]]
    if (is.name(base) && as.character(base) %in% known_frames) {
      return(list(derived_from = list(as.character(base)),
                  transform = list(op = "subset", expr = expr_text(rhs, 200))))
    }
  }
  if (is.na(fn)) return(NULL)
  # Known read functions → origin frame
  if (fn %in% READ_FNS) {
    p <- arg_by(rhs, name = "file") %||% arg_by(rhs, name = "input") %||% arg_by(rhs, pos = 1)
    pr <- arg_to_path(p, list())
    return(list(origin = pr$template,
                origin_kind = "file",
                transform = list(op = "read", fn = fn)))
  }
  # merge / *_join
  if (fn %in% c("merge","left_join","inner_join","right_join","full_join","anti_join",
                "dplyr::left_join","dplyr::inner_join","dplyr::right_join",
                "dplyr::full_join","dplyr::anti_join")) {
    refs <- intersect(extract_name_refs(rhs), known_frames)
    by_arg <- arg_by(rhs, name = "by")
    by_val <- if (is.character(by_arg)) as.list(by_arg)
              else if (is.call(by_arg) && identical(by_arg[[1]], as.name("c"))) {
                as.list(unlist(lapply(as.list(by_arg)[-1],
                                      function(x) if (is.character(x)) x else NA)))
              } else NULL
    return(list(derived_from = if (length(refs)) as.list(unique(refs)) else NULL,
                transform = list(op = "merge", by = by_val)))
  }
  # filter / subset
  if (fn %in% c("filter","subset","dplyr::filter")) {
    refs <- intersect(extract_name_refs(rhs), known_frames)
    args <- as.list(rhs)[-1]
    pred <- if (length(args) >= 2) expr_text(args[[2]], 200) else NULL
    return(list(derived_from = if (length(refs)) as.list(unique(refs)) else NULL,
                transform = list(op = "filter", predicate = pred)))
  }
  # rbind / bind_rows
  if (fn %in% c("rbind","rbindlist","bind_rows","dplyr::bind_rows")) {
    refs <- intersect(extract_name_refs(rhs), known_frames)
    return(list(derived_from = if (length(refs)) as.list(unique(refs)) else NULL,
                transform = list(op = "rbind")))
  }
  # Typecasts
  if (fn %in% c("as.data.frame","as_tibble","tibble::as_tibble","as.matrix",
                "column_to_rownames","rownames_to_column","tibble::column_to_rownames",
                "tibble::rownames_to_column")) {
    refs <- intersect(extract_name_refs(rhs), known_frames)
    return(list(derived_from = if (length(refs)) as.list(unique(refs)) else NULL,
                transform = list(op = "typecast", fn = fn)))
  }
  # Literal constructors — `data.frame(a=..., b=...)`, `tibble(...)`, `tribble(...)`.
  # Round-2: surface the named-arg keys as columns when the call is purely
  # named. This is the most common pattern for scripts that write a summary
  # TSV directly with `fwrite(data.frame(sample_id=..., n_reads=...), ...)`.
  if (fn %in% c("data.frame", "tibble", "tibble::tibble",
                "as_tibble", "tibble::as_tibble", "tribble")) {
    args <- as.list(rhs)[-1]
    arg_names <- names(args)
    if (!is.null(arg_names)) {
      cols <- arg_names[nzchar(arg_names)]
      # Drop common control kwargs that aren't columns
      cols <- setdiff(cols, c("stringsAsFactors", "check.names", "row.names",
                              "check.rows", "fix.empty.names"))
      if (length(cols)) {
        return(list(transform = list(op = "construct", fn = fn),
                    columns   = as.list(cols)))
      }
    }
    return(list(transform = list(op = "construct", fn = fn)))
  }
  # No generic fallback. Round-1 dataframes[] uses a positive allowlist of
  # dataframe-producing functions (READ_FNS, merge/joins, filter/subset,
  # rbind, typecasts, `[`, `%>%`). Anything else — model fits, ggplot
  # construction, scalar reductions, plot+geom chains — would create huge
  # noise. Surface as a "derived_unknown" finding only when there's clear
  # data manipulation: dplyr verbs by name.
  if (fn %in% c("mutate","transmute","summarise","summarize","arrange",
                "select","rename","group_by","ungroup",
                "pivot_longer","pivot_wider",
                "dplyr::mutate","dplyr::transmute","dplyr::summarise",
                "dplyr::arrange","dplyr::select","dplyr::rename",
                "tidyr::pivot_longer","tidyr::pivot_wider")) {
    refs <- intersect(extract_name_refs(rhs), known_frames)
    return(list(derived_from = if (length(refs)) as.list(unique(refs)) else NULL,
                transform = list(op = fn, expr = expr_text(rhs, 200))))
  }
  NULL
}

# Functions whose RHS is *never* a dataframe — used to filter out
# false positives like `t_yes <- sum(out[[a]] == "Yes")` from the
# generic "any call referencing a known frame" fallback.
SCALAR_FNS <- c("sum","mean","median","min","max","length","nrow","ncol",
                "any","all","sd","var","quantile","range","prod",
                "as.integer","as.numeric","as.double","as.logical",
                "is.na","is.null","is.character","is.numeric",
                "paste","paste0","sprintf","cat","print","message","stop",
                "warning")

collect_dataframes <- function(calls_all) {
  out <- list()
  known <- character()
  for (item in calls_all) {
    e <- item$call
    if (!(is.call(e) && length(e) == 3 &&
          (identical(e[[1]], as.name("<-")) || identical(e[[1]], as.name("="))))) next
    lhs <- e[[2]]; rhs <- e[[3]]
    if (!is.name(lhs)) next
    # Skip if RHS is a scalar-returning call
    fn <- if (is.call(rhs)) call_name(rhs) else NA_character_
    if (!is.na(fn) && fn %in% SCALAR_FNS) next
    cls <- df_classify(rhs, known)
    if (is.null(cls)) next
    entry <- list(id = as.character(lhs), site = item$line_start)
    entry[names(cls)] <- cls
    out[[length(out) + 1]] <- entry
    known <- unique(c(known, as.character(lhs)))
  }
  out
}

# Models
MODEL_FNS <- c(
  "DESeqDataSetFromMatrix", "DESeq2::DESeqDataSetFromMatrix",
  "lm", "stats::lm", "glm", "stats::glm",
  "lmer", "lme4::lmer",
  "lmFit", "limma::lmFit",
  "glmFit", "edgeR::glmFit",
  "glmQLFit", "edgeR::glmQLFit"
)
CONTRAST_FNS <- c("results", "DESeq2::results", "topTable", "limma::topTable",
                  "topTags", "edgeR::topTags", "glmLRT", "glmQLFTest")

# Find every `factor(<col>, levels = c(...))` call. Returns a named list
# `column_name -> first_level (= reference)`. Used by collect_models to
# attach reference_levels per term.
find_reference_levels <- function(calls_all, terms_universe) {
  if (!length(terms_universe)) return(NULL)
  out <- list()
  for (item in calls_all) {
    e <- item$call
    if (!identical(call_name(e), "factor")) next
    x_arg <- arg_by(e, pos = 1)
    lvl_arg <- arg_by(e, name = "levels")
    col_name <- NULL
    if (is.name(x_arg)) col_name <- as.character(x_arg)
    else if (is.call(x_arg) && length(x_arg) == 3 &&
             identical(x_arg[[1]], as.name("$"))) {
      col_name <- as.character(x_arg[[3]])
    }
    if (!is.null(col_name) && col_name %in% terms_universe &&
        is.call(lvl_arg) && identical(lvl_arg[[1]], as.name("c"))) {
      vals <- unlist(lapply(as.list(lvl_arg)[-1],
                            function(x) if (is.character(x)) x else NA))
      vals <- vals[!is.na(vals)]
      if (length(vals) && is.null(out[[col_name]])) out[[col_name]] <- vals[1]
    }
  }
  if (length(out)) out else NULL
}

collect_models <- function(calls_all) {
  models <- list(); contrasts <- list()
  for (item in calls_all) {
    e <- item$call
    if (!(is.call(e) && length(e) == 3 &&
          (identical(e[[1]], as.name("<-")) || identical(e[[1]], as.name("="))))) next
    lhs <- e[[2]]; rhs <- e[[3]]
    if (!(is.name(lhs) && is.call(rhs))) next
    fn <- call_name(rhs)
    if (is.na(fn)) next
    if (fn %in% MODEL_FNS) {
      design <- arg_by(rhs, name = "design") %||%
                arg_by(rhs, name = "formula") %||% arg_by(rhs, pos = 1)
      design_text <- if (!is.null(design)) expr_text(design, 100) else NULL
      countData <- arg_by(rhs, name = "countData") %||% arg_by(rhs, name = "data")
      colData   <- arg_by(rhs, name = "colData")
      models[[length(models) + 1]] <- list(
        id      = as.character(lhs),
        site    = item$line_start,
        fn      = fn,
        formula = design_text,
        count_data = if (is.name(countData)) as.character(countData) else NULL,
        col_data   = if (is.name(colData))   as.character(colData)   else NULL
      )
    } else if (fn %in% CONTRAST_FNS) {
      dds_ref <- arg_by(rhs, pos = 1)
      dds_name <- if (is.name(dds_ref)) as.character(dds_ref) else NULL
      contrasts[[length(contrasts) + 1]] <- list(
        id   = as.character(lhs),
        site = item$line_start,
        fn   = fn,
        model_id = dds_name
      )
    }
  }
  # Universe of formula terms (for reference-level lookup)
  all_terms <- unique(unlist(lapply(models, function(m) {
    if (is.null(m$formula)) return(character())
    setdiff(regmatches(m$formula,
                       gregexpr("[A-Za-z_][A-Za-z0-9_.]*", m$formula))[[1]],
            c("", "~"))
  })))
  ref_levels <- find_reference_levels(calls_all, all_terms)
  # Attach contrasts + best-effort reference_levels to each model
  for (i in seq_along(models)) {
    mid <- models[[i]]$id
    mc <- Filter(function(c) identical(c$model_id, mid), contrasts)
    models[[i]]$contrasts <- if (length(mc))
      lapply(mc, function(c) list(id = c$id, site = c$site, fn = c$fn))
      else list()
    if (!is.null(ref_levels) && length(ref_levels)) {
      models[[i]]$reference_levels <- ref_levels
    }
  }
  models
}

collect_env_vars <- function(calls_all) {
  read_out <- character(); written_out <- character()
  for (item in calls_all) {
    nm <- call_name(item$call)
    if (is.na(nm)) next
    if (nm == "Sys.getenv") {
      a <- arg_by(item$call, pos = 1)
      if (is.character(a)) read_out <- c(read_out, a)
    } else if (nm == "Sys.setenv") {
      args <- as.list(item$call)[-1]
      nms <- names(args) %||% rep("", length(args))
      written_out <- c(written_out, nms[nzchar(nms)])
    }
  }
  list(env_vars_read = unique(read_out), env_vars_written = unique(written_out))
}

# ---------------------------------------------------------------------------
# Compliance checks (Layer A — see 02_inference_design.md §3.6 + §6)
# ---------------------------------------------------------------------------
compliance_checks <- function(parse_tree, calls_all, raw_lines, config_iface,
                              stoch_ops, inputs_l, outputs_l) {
  out <- list()
  push <- function(rule, status, evidence_sites = list(), note = NULL) {
    out[[length(out) + 1]] <<- list(rule = rule, status = status,
                                    evidence_sites = evidence_sites, note = note)
  }
  # script-header-metadata: author + date + Purpose in first 10 comment lines.
  # Accept both "Author:" and "Name:" as the author identifier; the CLAUDE.md
  # convention is "Author:" but "name:" / "Name:" appears in the lab corpus.
  head_comments <- raw_lines[seq_len(min(10, length(raw_lines)))]
  head_comments <- head_comments[grepl("^\\s*#", head_comments)]
  has_author  <- any(grepl("(?i)(^|[^a-z])(author|name)\\s*:", head_comments, perl = TRUE))
  has_date    <- any(grepl("(?i)date|[0-9]{4}-[0-9]{2}-[0-9]{2}", head_comments, perl = TRUE))
  has_purpose <- any(grepl("(?i)purpose|description", head_comments, perl = TRUE))
  push("script-header-metadata",
       if (has_author && (has_date || has_purpose)) "pass" else "fail",
       evidence_sites = if (length(head_comments)) list(1L) else list(),
       note = if (!has_author) "no `# Author:` (or `# Name:`) line in first 10 comment lines"
              else if (!has_date && !has_purpose) "missing Date or Purpose"
              else NULL)

  # relative-paths-only: every config_interface default with default_kind=='absolute' → fail
  abs_opts <- Filter(function(o) identical(o$default_kind, "absolute"), config_iface$options)
  if (length(abs_opts)) {
    push("relative-paths-only", "fail",
         evidence_sites = lapply(abs_opts, function(o) o$site),
         note = sprintf("%d CLI defaults are absolute paths", length(abs_opts)))
  } else {
    push("relative-paths-only", "pass")
  }

  # forbidden-variable-names: any top-level assignment to a forbidden name
  forbidden_found <- list()
  rec <- function(e) {
    if (is.call(e) && length(e) == 3 &&
        (identical(e[[1]], as.name("<-")) || identical(e[[1]], as.name("=")) ||
         identical(e[[1]], as.name("<<-")))) {
      lhs <- e[[2]]
      if (is.name(lhs) && as.character(lhs) %in% FORBIDDEN_NAMES) {
        sr <- attr(e, "srcref")
        forbidden_found[[length(forbidden_found) + 1]] <<-
          list(name = as.character(lhs), site = if (!is.null(sr)) sr[[1]] else NA_integer_)
      }
    }
    if (is.call(e) || is.expression(e)) for (i in seq_along(e)) rec(e[[i]])
  }
  if (is.expression(parse_tree)) for (i in seq_along(parse_tree)) rec(parse_tree[[i]])
  if (length(forbidden_found)) {
    push("forbidden-variable-names", "fail",
         evidence_sites = lapply(forbidden_found, function(x) x$site),
         note = paste("collisions:", paste(unique(vapply(forbidden_found, `[[`, "", "name")), collapse = ",")))
  } else {
    push("forbidden-variable-names", "pass")
  }

  # seed-coverage: every stochastic op has seed_set TRUE
  if (length(stoch_ops) == 0) {
    push("seed-coverage", "n/a", note = "no stochastic ops detected")
  } else {
    unseeded <- Filter(function(s) !isTRUE(s$seed_set), stoch_ops)
    if (length(unseeded)) {
      push("seed-coverage", "fail",
           evidence_sites = lapply(unseeded, function(s) s$site),
           note = sprintf("%d/%d stochastic ops have no reaching set.seed",
                          length(unseeded), length(stoch_ops)))
    } else {
      push("seed-coverage", "pass",
           evidence_sites = lapply(stoch_ops, function(s) s$site))
    }
  }

  # ===== BLOCKERs =====

  # raw-data-write: any output path under data/raw/ → BLOCKER
  raw_writes <- Filter(function(o) {
    p <- o$path_template %||% ""
    grepl("(^|/)data/raw/|(^|/)raw/", p)
  }, outputs_l)
  if (length(raw_writes)) {
    push("raw-data-write", "fail",
         evidence_sites = lapply(raw_writes, function(o) o$write_call$site),
         note = sprintf("%d output(s) resolve under data/raw/; raw data is immutable",
                        length(raw_writes)))
  } else {
    push("raw-data-write", "pass")
  }

  # header-preserved: any read call with header=FALSE / col.names=FALSE
  # (round 1: doesn't yet verify if a colnames(...)<- recovery follows;
  # explicit drop is sufficient cause for BLOCKER per CLAUDE.md §2)
  header_dropped <- Filter(function(x) isTRUE(x$header_dropped), inputs_l)
  if (length(header_dropped)) {
    push("header-preserved", "fail",
         evidence_sites = lapply(header_dropped, function(x) x$read_call$site),
         note = sprintf("%d read call(s) drop headers explicitly (header=FALSE / col.names=FALSE)",
                        length(header_dropped)))
  } else {
    push("header-preserved", "pass")
  }

  # hardcoded-contig: any "chrN" / "chrXY" / "chrMT" literal in non-comment
  # code. Mirrors block-hardcoded-contigs.sh from CLAUDE.md hooks.
  contig_re <- "[\"']chr([0-9]+|[XYM]|MT)[\"']"
  contig_hits <- integer()
  for (i in seq_along(raw_lines)) {
    line <- raw_lines[i]
    if (grepl("^\\s*#", line)) next
    code <- sub("#[^\"']*$", "", line)
    if (grepl(contig_re, code, perl = TRUE)) contig_hits <- c(contig_hits, i)
  }
  if (length(contig_hits)) {
    push("hardcoded-contig", "fail",
         evidence_sites = as.list(contig_hits),
         note = sprintf("%d line(s) contain hardcoded contig literals (chrN / chrXY / chrMT)",
                        length(contig_hits)))
  } else {
    push("hardcoded-contig", "pass")
  }

  # logging-dual-capture: presence of sink(..., split=TRUE) and globalCallingHandlers
  has_sink_split <- FALSE; sink_site <- NA_integer_
  has_gch_msg    <- FALSE; gch_site  <- NA_integer_
  for (item in calls_all) {
    nm <- call_name(item$call)
    if (identical(nm, "sink")) {
      sp <- arg_by(item$call, name = "split")
      if (identical(sp, TRUE)) { has_sink_split <- TRUE; sink_site <- item$line_start }
    } else if (identical(nm, "globalCallingHandlers")) {
      args <- as.list(item$call)[-1]
      if ("message" %in% names(args)) { has_gch_msg <- TRUE; gch_site <- item$line_start }
    }
  }
  if (has_sink_split && has_gch_msg) {
    push("logging-dual-capture", "pass",
         evidence_sites = list(sink_site, gch_site))
  } else if (has_sink_split || has_gch_msg) {
    push("logging-dual-capture", "fail",
         note = "partial: need both sink(split=TRUE) and globalCallingHandlers(message=…)")
  } else {
    push("logging-dual-capture", "fail",
         note = "no log-capture setup detected")
  }

  out
}

# ---------------------------------------------------------------------------
# Audit findings preview — derived from compliance_checks + heuristics
# ---------------------------------------------------------------------------
SEVERITY_MAP <- c(
  # BLOCKERs gate the audit (red rules from CLAUDE.md §6)
  "raw-data-write"           = "BLOCKER",
  "header-preserved"         = "BLOCKER",
  "hardcoded-contig"         = "BLOCKER",
  # WARNINGs require review
  "relative-paths-only"      = "WARNING",
  "forbidden-variable-names" = "WARNING",
  "seed-coverage"            = "WARNING",
  "genome-build-tag"         = "WARNING",
  # NOTEs are advisory
  "logging-dual-capture"     = "NOTE",
  "script-header-metadata"   = "NOTE"
)

findings_from_compliance <- function(checks) {
  out <- list()
  for (c in checks) {
    if (identical(c$status, "fail")) {
      sev <- SEVERITY_MAP[[c$rule]] %||% "NOTE"
      out[[length(out) + 1]] <- list(severity = sev, rule = c$rule,
                                     sites = c$evidence_sites, note = c$note)
    } else if (identical(c$status, "pass")) {
      out[[length(out) + 1]] <- list(severity = "OK", rule = c$rule,
                                     note = c$note %||% paste("compliance check passed:", c$rule))
    }
  }
  out
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
raw_lines  <- readLines(opt$input, warn = FALSE)
parse_tree <- parse(file = opt$input, keep.source = TRUE)
line_map   <- build_call_line_map(parse_tree)
calls_all  <- walk_collect(parse_tree, line_map)
assigns    <- collect_simple_assigns(parse_tree)

packages       <- collect_packages(calls_all)
config_iface   <- collect_config_interface(calls_all)
inputs         <- collect_inputs(calls_all, assigns)
outputs        <- collect_outputs(calls_all, assigns)
side_effects   <- collect_side_effects(calls_all)
stoch_ops      <- collect_stochastic_ops(calls_all)
env_vars       <- collect_env_vars(calls_all)
hardcoded_data <- collect_hardcoded_data(calls_all, raw_lines)
dataframes_l   <- collect_dataframes(calls_all)
# Round-2: surface output → dataframe linkage so casetrack_check.py can
# recover written column lists when validating FK / prefix collisions.
outputs        <- link_outputs_to_dataframes(outputs, dataframes_l, calls_all)
models_l       <- collect_models(calls_all)
casetrack_appends <- extract_casetrack_appends(paste(raw_lines, collapse = "\n"))
checks         <- compliance_checks(parse_tree, calls_all, raw_lines,
                                    config_iface, stoch_ops, inputs, outputs)
findings       <- findings_from_compliance(checks)

# seed_policy summary
seed_policy <- if (length(stoch_ops) == 0) {
  list(declared_value = NULL,
       coverage       = list(stochastic_ops = 0L, seeded = 0L, unseeded = 0L),
       severity       = "n/a")
} else {
  seeded <- sum(vapply(stoch_ops, function(s) isTRUE(s$seed_set), logical(1)))
  vals <- unique(stats::na.omit(vapply(stoch_ops, function(s) s$seed_value %||% NA_integer_, integer(1))))
  declared <- if (length(vals) == 1) as.integer(vals) else NULL  # single-value scripts only
  CLAUDE_DEFAULT_SEED <- 42L
  divergent <- !is.null(declared) && !identical(declared, CLAUDE_DEFAULT_SEED)
  list(declared_value = declared,
       multiple_values_observed = if (length(vals) > 1) as.list(as.integer(vals)) else NULL,
       coverage       = list(stochastic_ops = as.integer(length(stoch_ops)),
                             seeded         = as.integer(seeded),
                             unseeded       = as.integer(length(stoch_ops) - seeded)),
       divergence_from_claude_default = divergent,
       severity       = if (seeded < length(stoch_ops)) "WARNING" else if (divergent) "NOTE" else "OK",
       note = if (divergent) sprintf("seed=%d used across %d stochastic ops; CLAUDE.md default is %d",
                                     declared, length(stoch_ops), CLAUDE_DEFAULT_SEED) else NULL)
}

# Organism / genome inference: package allowlist hits
org_db_hits <- grep("^org\\.[A-Z][a-z]\\.eg\\.db$", packages, value = TRUE)
organism_inferred <- if (length(org_db_hits)) {
  switch(org_db_hits[1],
         "org.Mm.eg.db" = "mouse",
         "org.Hs.eg.db" = "human",
         "org.Rn.eg.db" = "rat",
         "unknown")
} else NULL
all_paths <- c(vapply(inputs, function(x) x$path_template %||% "", character(1)),
               vapply(outputs, function(x) x$path_template %||% "", character(1)))
gb_tokens <- c("mm10","mm39","GRCm39","hg38","GRCh38","hg19","GRCh37","t2t","chm13")
genome_build_declared <- {
  hit <- gb_tokens[vapply(gb_tokens, function(t) any(grepl(t, all_paths, fixed = TRUE)), logical(1))]
  if (length(hit)) hit[1] else NULL
}

# Cross-field finding: organism inferred but no genome build tag → WARNING.
# This is derived after the per-rule compliance pass; appended in place.
if (!is.null(organism_inferred) && is.null(genome_build_declared)) {
  checks[[length(checks) + 1]] <- list(
    rule = "genome-build-tag",
    status = "fail",
    evidence_sites = list(),
    note = sprintf("organism inferred=%s but no genome build (mm10/mm39/GRCm39/hg38/...) declared in any path", organism_inferred)
  )
  findings[[length(findings) + 1]] <- list(
    severity = "WARNING",
    rule = "genome-build-tag",
    sites = list(),
    note = sprintf("organism inferred=%s; no genome build token in inputs/outputs", organism_inferred)
  )
}

# Append seed-policy as a finding when severity is NOTE / WARNING
if (!is.null(seed_policy$severity) && seed_policy$severity %in% c("NOTE", "WARNING")) {
  sev <- if (identical(seed_policy$severity, "WARNING")) "WARNING" else "NOTE"
  findings[[length(findings) + 1]] <- list(
    severity = sev,
    rule = "seed-policy",
    note = seed_policy$note %||% "see seed_policy block"
  )
}

# ---------------------------------------------------------------------------
# Optional: parse launcher and compose pair_unit
# ---------------------------------------------------------------------------
pair_unit <- NULL
analysis_kind <- "single"
if (!is.null(opt$pair_launcher)) {
  if (!file.exists(opt$pair_launcher)) {
    stop("pair_launcher not found: ", opt$pair_launcher)
  }
  bash_parser <- resolve_bash_parser(opt$bash_parser)
  if (is.null(bash_parser) || !file.exists(bash_parser)) {
    stop("could not locate sciauditor_bash.py; pass --bash_parser <path>")
  }
  tmp_yaml <- tempfile(fileext = ".yaml")
  on.exit(unlink(tmp_yaml), add = TRUE)
  rc <- system2("python3", c(shQuote(bash_parser),
                             "--input",  shQuote(opt$pair_launcher),
                             "--output", shQuote(tmp_yaml)),
                stderr = FALSE)
  if (rc != 0) stop("sciauditor_bash.py failed on ", opt$pair_launcher)
  launcher <- yaml::read_yaml(tmp_yaml)

  # Effective cwd: first `cd` side_effect in the launcher
  cd_se <- Filter(function(s) identical(s$kind, "cd"), launcher$side_effects)
  eff_cwd <- if (length(cd_se)) cd_se[[1]]$detail else NULL

  # Build binding[]: launcher_var ↔ analysis_flag whose names match the
  # analysis-side config_interface.options
  analysis_flags <- vapply(config_iface$options,
                           function(o) o$name %||% NA_character_,
                           character(1))
  binding <- list()
  if (!is.null(launcher$invocation) &&
      !is.null(launcher$invocation$flags)) {
    for (f in launcher$invocation$flags) {
      if (is.null(f$value_var)) next
      match_idx <- which(analysis_flags == f$flag)
      analysis_site <- if (length(match_idx))
        config_iface$options[[match_idx[1]]]$site else NA_integer_
      # Find the launcher-side site by var name
      launcher_site <- NA_integer_
      for (o in launcher$config_interface$options) {
        if (identical(o$name, f$value_var)) { launcher_site <- o$site; break }
      }
      binding[[length(binding) + 1]] <- list(
        launcher_var   = f$value_var,
        analysis_flag  = f$flag,
        value_resolved = f$value_resolved,
        site = sprintf("launcher:%s → analysis:%s",
                       as.character(launcher_site),
                       as.character(analysis_site))
      )
    }
  }
  pair_unit <- list(
    launcher = list(path = opt$pair_launcher, language = "bash"),
    analysis = list(path = opt$input,          language = "R"),
    binding  = binding,
    effective_cwd_at_analysis = eff_cwd
  )
  analysis_kind <- "pair"

  # Cross-pair finding: any analysis flag with no launcher binding → WARNING
  unbound <- setdiff(analysis_flags,
                     vapply(binding, function(b) b$analysis_flag, character(1)))
  unbound <- unbound[!is.na(unbound)]
  if (length(unbound)) {
    findings[[length(findings) + 1]] <- list(
      severity = "NOTE",
      rule = "pair-binding-coverage",
      note = sprintf("%d analysis CLI option(s) not bound by launcher (will use defaults): %s",
                     length(unbound), paste(unbound, collapse = ", "))
    )
  }
}

# Assemble the v0.2 YAML root
analysis_id <- opt$analysis_unit_id %||% tools::file_path_sans_ext(basename(opt$input))
root <- list(
  schema_version = opt$schema_version,
  analysis_unit = list(id = analysis_id, kind = analysis_kind),
  pair_unit = pair_unit,
  script = list(
    path        = opt$input,
    language    = "R",
    git_rev     = "<runtime>",
    inferred_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
    layers_used = list("static")
  ),
  runtime_context = list(
    cwd_at_invocation = "<runtime>",
    resolved_cwd      = "<runtime>",
    host              = "<runtime>",
    user              = "<runtime>"
  ),
  config_interface = config_iface,
  inputs           = inputs,
  outputs          = outputs,
  package_resources = NULL,   # not yet implemented
  env_vars_read    = as.list(env_vars$env_vars_read),
  env_vars_written = as.list(env_vars$env_vars_written),
  dataframes       = dataframes_l,
  transformations  = list(),  # still deferred — predicate-extraction is partial in dataframes[]
  models           = models_l,
  figures          = list(),
  stochastic_ops   = stoch_ops,
  seed_policy      = seed_policy,
  functions_defined = NULL,
  hardcoded_data   = if (length(hardcoded_data)) hardcoded_data else NULL,
  external_binaries = list(),
  driver_pattern   = NULL,
  validation       = NULL,
  side_effects     = side_effects,
  environment      = list(r_packages = as.list(packages), container = NULL),
  organism_inferred = organism_inferred,
  genome_build_declared = genome_build_declared,
  casetrack_appends = casetrack_appends,
  compliance_checks = checks,
  audit_findings_preview = findings,
  unresolved = list(
    list(kind = "not_yet_implemented",
         note = "round 1.5: transformations[] / figures[] / functions_defined / pair_unit / runtime trace still deferred")
  )
)

# ---------------------------------------------------------------------------
# Scored audit report (Option C)
# ---------------------------------------------------------------------------
# Map each compliance rule to a category for per-axis scoring. Rules not
# listed here fall into "misc".
RULE_CATEGORIES <- list(
  "script-header-metadata"   = "reproducibility",
  "logging-dual-capture"     = "reproducibility",
  "seed-coverage"            = "reproducibility",
  "seed-policy"              = "reproducibility",
  "relative-paths-only"      = "io",
  "raw-data-write"           = "io",
  "header-preserved"         = "io",
  "forbidden-variable-names" = "variables",
  "genome-build-tag"         = "genomics",
  "hardcoded-contig"         = "genomics"
)

grade_pct <- function(p) {
  if (is.na(p)) return("N/A")
  if (p >= 0.90) "A" else if (p >= 0.80) "B" else if (p >= 0.70) "C"
  else if (p >= 0.60) "D" else "F"
}

emit_report <- function(root, report_dir) {
  dir.create(report_dir, recursive = TRUE, showWarnings = FALSE)

  # Pass/fail counts by category (from compliance_checks)
  cat_pass <- list(); cat_fail <- list()
  for (chk in root$compliance_checks) {
    cat_name <- RULE_CATEGORIES[[chk$rule]] %||% "misc"
    if (identical(chk$status, "pass")) cat_pass[[cat_name]] <- (cat_pass[[cat_name]] %||% 0L) + 1L
    if (identical(chk$status, "fail")) cat_fail[[cat_name]] <- (cat_fail[[cat_name]] %||% 0L) + 1L
  }
  cats <- sort(unique(c(names(cat_pass), names(cat_fail))))
  total_pass <- sum(unlist(cat_pass) %||% 0L)
  total_fail <- sum(unlist(cat_fail) %||% 0L)
  headline_pct <- if (total_pass + total_fail == 0) NA_real_
                  else total_pass / (total_pass + total_fail)

  lines <- c(
    "# sciAuditor — Audit Report",
    "",
    sprintf("- **Analysis**: `%s`", root$script$path),
    sprintf("- **Inferred at**: %s", root$script$inferred_at),
    sprintf("- **Schema**: v%s · Layer A (static)", root$schema_version),
    "",
    "## Headline",
    "",
    "| Score | Grade |",
    "|---|---|",
    sprintf("| %d / %d (%s) | **%s** |",
            total_pass, total_pass + total_fail,
            if (is.na(headline_pct)) "—" else sprintf("%.0f%%", 100 * headline_pct),
            grade_pct(headline_pct)),
    "",
    "## By category",
    "",
    "| Category | Pass | Fail | %  | Grade |",
    "|---|---:|---:|---:|---:|"
  )
  for (cat_name in cats) {
    p <- cat_pass[[cat_name]] %||% 0L; f <- cat_fail[[cat_name]] %||% 0L
    pct <- if (p + f == 0) NA_real_ else p / (p + f)
    lines <- c(lines, sprintf("| %s | %d | %d | %s | %s |",
                              cat_name, p, f,
                              if (is.na(pct)) "—" else sprintf("%.0f%%", 100 * pct),
                              grade_pct(pct)))
  }

  # Findings grouped by severity
  lines <- c(lines, "", "## Findings", "")
  for (sev in c("BLOCKER", "WARNING", "NOTE", "OK")) {
    hits <- Filter(function(f) identical(f$severity, sev), root$audit_findings_preview)
    if (!length(hits)) next
    lines <- c(lines, sprintf("### %s (%d)", sev, length(hits)), "")
    for (h in hits) {
      sites <- h$sites %||% h$evidence_sites %||% list()
      sites_text <- if (length(sites)) sprintf(" (L%s)", paste(unlist(sites), collapse = ", L")) else ""
      lines <- c(lines, sprintf("- **%s**%s — %s",
                                h$rule, sites_text, h$note %||% ""))
    }
    lines <- c(lines, "")
  }

  # Inventory
  sp_seeded   <- root$seed_policy$coverage$seeded   %||% 0L
  sp_unseeded <- root$seed_policy$coverage$unseeded %||% 0L
  lines <- c(lines, "## Inventory", "",
             sprintf("- Inputs: **%d**", length(root$inputs)),
             sprintf("- Outputs: **%d**", length(root$outputs)),
             sprintf("- Models: **%d**", length(root$models)),
             sprintf("- Dataframes: **%d**", length(root$dataframes)),
             sprintf("- Stochastic ops: **%d** (%d seeded, %d unseeded)",
                     length(root$stochastic_ops), sp_seeded, sp_unseeded),
             sprintf("- Hardcoded blocks: **%d**",
                     length(root$hardcoded_data %||% list())),
             sprintf("- Organism inferred: **%s**",
                     root$organism_inferred %||% "not detected"),
             sprintf("- Genome build declared: **%s**",
                     root$genome_build_declared %||% "_not declared_")
  )

  if (length(root$models)) {
    lines <- c(lines, "", "## Models", "")
    for (m in root$models) {
      lines <- c(lines, sprintf("- `%s` (L%s) — `%s` design `%s`",
                                m$id, m$site %||% "?",
                                m$fn, m$formula %||% "?"))
      if (length(m$contrasts)) {
        contrast_names <- vapply(m$contrasts, function(c) c$id, character(1))
        lines <- c(lines, sprintf("  - contrasts: %s",
                                  paste(paste0("`", contrast_names, "`"), collapse = ", ")))
      }
    }
  }

  if (!is.null(root$pair_unit)) {
    pu <- root$pair_unit
    lines <- c(lines, "", "## Pair binding", "",
               sprintf("- **Launcher**: `%s`", pu$launcher$path),
               sprintf("- **Analysis**: `%s`", pu$analysis$path),
               sprintf("- **Effective cwd at analysis**: `%s`",
                       pu$effective_cwd_at_analysis %||% "_not detected_"),
               "",
               sprintf("**Bindings (%d):**", length(pu$binding)),
               "",
               "| Launcher var | Analysis flag | Resolved value | Sites |",
               "|---|---|---|---|")
    for (b in pu$binding) {
      val <- as.character(b$value_resolved %||% "")
      if (nchar(val) > 60) val <- paste0(substr(val, 1, 57), "...")
      lines <- c(lines, sprintf("| `%s` | `%s` | `%s` | %s |",
                                b$launcher_var %||% "?",
                                b$analysis_flag %||% "?",
                                val, b$site %||% "?"))
    }
  }

  report_path <- file.path(report_dir, "audit_report.md")
  writeLines(lines, report_path)

  # Machine-readable findings TSV for CI
  tsv_path <- file.path(report_dir, "audit_findings.tsv")
  tsv_lines <- c("severity\trule\tsites\tnote")
  for (f in root$audit_findings_preview) {
    sites <- f$sites %||% f$evidence_sites %||% list()
    sites_text <- paste(unlist(sites), collapse = ",")
    note <- gsub("\t", " ", f$note %||% "")
    tsv_lines <- c(tsv_lines, sprintf("%s\t%s\t%s\t%s",
                                      f$severity, f$rule, sites_text, note))
  }
  writeLines(tsv_lines, tsv_path)

  list(report = report_path,
       findings_tsv = tsv_path,
       headline_score = sprintf("%d/%d %s",
                                total_pass, total_pass + total_fail,
                                grade_pct(headline_pct)))
}

# Emit YAML
yaml_str <- as.yaml(root, indent = 2, indent.mapping.sequence = TRUE)
if (identical(opt$output, "-")) {
  cat(yaml_str)
} else {
  dir.create(dirname(opt$output), recursive = TRUE, showWarnings = FALSE)
  writeLines(yaml_str, opt$output)
  message(sprintf("[sciauditor_r] wrote %s (%d inputs, %d outputs, %d findings)",
                  opt$output, length(inputs), length(outputs), length(findings)))
}

# Emit report if requested
if (!is.null(opt$report_dir)) {
  res <- emit_report(root, opt$report_dir)
  message(sprintf("[sciauditor_r] report: %s  findings_tsv: %s  headline: %s",
                  res$report, res$findings_tsv, res$headline_score))
}
