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
  make_option(c("--analysis_unit_id"), type = "character", default = NULL,
              help = "override analysis_unit.id; defaults to basename of input"),
  make_option(c("--schema_version"), type = "character", default = "0.2",
              help = "[default %default]")
)
opt <- parse_args(OptionParser(option_list = option_list))
if (is.null(opt$input)) stop("must pass --input")
if (!file.exists(opt$input)) stop("input not found: ", opt$input)

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

# Build a per-function-name FIFO of call-site line numbers from getParseData.
# This sidesteps the srcref-on-nested-call problem: the parse-data table is
# flat and lists every `SYMBOL_FUNCTION_CALL` token with its line number.
build_call_line_map <- function(parse_tree) {
  pd <- utils::getParseData(parse_tree)
  out <- new.env(parent = emptyenv())
  if (is.null(pd) || nrow(pd) == 0) return(out)
  rows <- pd[pd$token == "SYMBOL_FUNCTION_CALL", c("line1","text"), drop = FALSE]
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
    out[[length(out) + 1]] <- list(
      id              = sprintf("input_%02d", length(out) + 1),
      path_template   = pr$template,
      kind            = "tabular",
      format          = guess_format_from_fn(nm, pr$template),
      read_call       = list(fn = nm, site = item$line_start),
      resolution_confidence = pr$confidence
    )
  }
  out
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
compliance_checks <- function(parse_tree, calls_all, raw_lines, config_iface, stoch_ops) {
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
findings_from_compliance <- function(checks) {
  out <- list()
  for (c in checks) {
    if (identical(c$status, "fail")) {
      sev <- switch(c$rule,
                    "relative-paths-only"      = "WARNING",
                    "forbidden-variable-names" = "WARNING",
                    "seed-coverage"            = "WARNING",
                    "logging-dual-capture"     = "NOTE",
                    "script-header-metadata"   = "NOTE",
                    "NOTE")
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
checks         <- compliance_checks(parse_tree, calls_all, raw_lines, config_iface, stoch_ops)
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

# Assemble the v0.2 YAML root
analysis_id <- opt$analysis_unit_id %||% tools::file_path_sans_ext(basename(opt$input))
root <- list(
  schema_version = opt$schema_version,
  analysis_unit = list(id = analysis_id, kind = "single"),
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
  dataframes       = list(),  # not yet implemented (needs §3.2 column lineage)
  transformations  = list(),  # not yet implemented (needs predicate extraction)
  models           = list(),
  figures          = list(),
  stochastic_ops   = stoch_ops,
  seed_policy      = seed_policy,
  functions_defined = NULL,
  hardcoded_data   = NULL,
  external_binaries = list(),
  driver_pattern   = NULL,
  validation       = NULL,
  side_effects     = side_effects,
  environment      = list(r_packages = as.list(packages), container = NULL),
  organism_inferred = organism_inferred,
  genome_build_declared = genome_build_declared,
  compliance_checks = checks,
  audit_findings_preview = findings,
  unresolved = list(
    list(kind = "not_yet_implemented",
         note = "round-1 parser scope: dataframes/transformations/models/figures/functions_defined/hardcoded_data not yet populated")
  )
)

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
