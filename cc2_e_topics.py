"""
CC2-E Embedding topic model — does the keyword taxonomy MISS anything?

Design:
- ONE embedding model (all-MiniLM-L6-v2). BERTopic (numba/umap/hdbscan all import on
  this stack). Discover topics on NEGATIVE reviews only (5-star is thin/generic).
- Core deliverable = cluster x keyword-theme CROSSWALK: how much of the embedding
  structure the 10-theme taxonomy reproduces (coverage), which clusters are NOVEL
  (no existing theme >30% overlap, hand-verified), which are fragmented.
- Report the HDBSCAN outlier rate honestly.
- This is an independent SECOND method; convergence with keywords is the headline,
  novelty is the bonus. E is droppable to an appendix if it merely re-derives keywords.

Run: ./.venv/bin/python cc2_e_topics.py
"""
import numpy as np
import pandas as pd

import cc2_common as cc

OUT = cc.OUT
plt = cc.apply_chart_style()
NOVELTY_THRESHOLD = 0.30


def main():
    cc.ensure_dirs()
    df = cc.load_trustpilot()
    neg = cc.negatives(df)
    neg = neg[neg["review_text"].fillna("").str.split().apply(len) >= 5].reset_index(drop=True)
    docs = neg["review_text"].fillna("").tolist()
    print(f"Clustering {len(docs)} negative reviews (>=5 words).")

    from sentence_transformers import SentenceTransformer
    from umap import UMAP
    from hdbscan import HDBSCAN
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import CountVectorizer
    from bertopic import BERTopic

    embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = embed_model.encode(docs, show_progress_bar=False, batch_size=64)
    print(f"Embedded -> shape {embeddings.shape}")

    # Methodology note: HDBSCAN collapses these short, highly-similar complaint texts into
    # one ~88% mega-cluster (not useful for sub-theme discovery). We disclose that and use
    # KMeans(k=14) for a stable, interpretable forced partition — finer than the 10 keyword
    # themes so genuinely novel structure has room to appear.
    K = 14
    umap_model = UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=42)
    cluster_model = KMeans(n_clusters=K, random_state=42, n_init=10)
    vectorizer = CountVectorizer(stop_words="english", ngram_range=(1, 2), min_df=3)
    topic_model = BERTopic(embedding_model=embed_model, umap_model=umap_model,
                           hdbscan_model=cluster_model, vectorizer_model=vectorizer,
                           calculate_probabilities=False, verbose=False)
    topics, _ = topic_model.fit_transform(docs, embeddings)
    neg["topic"] = topics

    info = topic_model.get_topic_info()
    n_topics = (info["Topic"] >= 0).sum()
    outlier_rate = (np.array(topics) == -1).mean()   # KMeans -> 0 outliers (no -1 bucket)
    print(f"Found {n_topics} KMeans topics (k={K}); outlier rate = {outlier_rate:.1%}")

    # ---- crosswalk: each topic's dominant keyword theme + overlap
    rows = []
    for t in sorted(set(topics)):
        if t == -1:
            continue
        sub = neg[neg["topic"] == t]
        overlaps = {th: sub[f"th_{th}"].mean() for th in cc.THEMES}
        dom = max(overlaps, key=overlaps.get)
        dom_ov = overlaps[dom]
        words = ", ".join([w for w, _ in topic_model.get_topic(t)[:8]])
        rows.append(dict(topic=t, size=len(sub), top_words=words,
                         dominant_theme=dom, overlap_pct=round(dom_ov, 3),
                         novelty_flag=bool(dom_ov < NOVELTY_THRESHOLD),
                         neg_share=round(sub["neg"].mean(), 3)))
    cw = pd.DataFrame(rows).sort_values("size", ascending=False)
    cw.to_csv(f"{OUT}/CC2_cluster_theme_crosswalk.csv", index=False)

    # coverage = share of clustered (non-outlier) negatives in topics explained by an existing theme
    clustered = cw["size"].sum()
    explained = cw[~cw["novelty_flag"]]["size"].sum()
    coverage = explained / clustered if clustered else np.nan
    novel = cw[cw["novelty_flag"]]
    print(f"Taxonomy coverage of embedding structure: {coverage:.0%} of clustered negatives "
          f"fall in topics dominated by an existing theme. Novel candidate topics: {len(novel)}.")

    # ---- novel topic exemplars (hand-verify before naming)
    lines = ["# CC2-E — Candidate novel topics (keyword taxonomy <30% overlap)\n",
             "These are clusters the keyword themes do NOT explain. Exemplars listed for manual verification — ",
             "a cluster is only a real 'new theme' after a human reads these.\n"]
    if len(novel) == 0:
        lines.append("\n**None found** — every embedding cluster is dominated by an existing keyword theme. ",
                     )
        lines.append("This is itself a strong validation result: the taxonomy reproduces the embedding structure.\n")
    for r in novel.itertuples():
        sub = neg[neg["topic"] == r.topic]
        lines.append(f"\n## Topic {r.topic} (n={r.size}, top theme {r.dominant_theme} only {r.overlap_pct:.0%})")
        lines.append(f"**Top words:** {r.top_words}\n")
        for ex in sub["review_text"].head(5):
            lines.append(f"- {str(ex)[:160]}")
    with open(f"{OUT}/CC2_novel_topics_exemplars.md", "w") as f:
        f.write("\n".join(lines))

    # ---- topics over time (quarterly), best-effort
    try:
        timestamps = neg["published_date"].dt.tz_convert(None).tolist()
        tot = topic_model.topics_over_time(docs, timestamps, nr_bins=14)
        tot.to_csv(f"{OUT}/CC2_topics_over_time.csv", index=False)
        have_tot = True
    except Exception as ex:
        print(f"(topics_over_time skipped: {type(ex).__name__})")
        have_tot = False

    # ============================================================ charts
    # E1 2-D landscape
    umap2d = UMAP(n_neighbors=15, n_components=2, min_dist=0.1, metric="cosine", random_state=42).fit_transform(embeddings)
    fig, ax = plt.subplots(figsize=(9, 7))
    mask = np.array(topics) != -1
    sc = ax.scatter(umap2d[mask, 0], umap2d[mask, 1], c=np.array(topics)[mask], cmap="tab20", s=6, alpha=0.6)
    ax.scatter(umap2d[~mask, 0], umap2d[~mask, 1], color="lightgray", s=4, alpha=0.3, label=f"outliers ({outlier_rate:.0%})")
    ax.set_title(f"Embedding landscape of negative reviews — {n_topics} topics (MiniLM + UMAP + HDBSCAN)")
    ax.legend(fontsize=8); ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/E1_topic_landscape.png"); plt.close()

    # E3 coverage bar (dominant theme distribution)
    theme_cov = cw.groupby("dominant_theme")["size"].sum().sort_values()
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [cc.GRAY if th in cw[cw.novelty_flag]["dominant_theme"].values else cc.NAVY for th in theme_cov.index]
    ax.barh(theme_cov.index, theme_cov.values, color=cc.NAVY)
    ax.set_xlabel("Negative reviews in topics dominated by this theme")
    ax.set_title(f"Embedding clusters map onto keyword themes — {coverage:.0%} coverage, {len(novel)} novel")
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/E3_coverage_bar.png"); plt.close()

    # E2 topics over time (if available) — top topics
    if have_tot:
        try:
            top_ids = cw.head(6)["topic"].tolist()
            fig, ax = plt.subplots(figsize=(11, 5))
            for tid in top_ids:
                d = tot[tot["Topic"] == tid]
                if len(d):
                    lbl = cw[cw.topic == tid]["dominant_theme"].iloc[0]
                    ax.plot(pd.to_datetime(d["Timestamp"]), d["Frequency"], marker="o", ms=3, label=f"T{tid}:{lbl}")
            ax.set_title("Topics over time (embedding-discovered) — cross-check vs keyword growth")
            ax.legend(fontsize=7, ncol=2); ax.set_ylabel("Frequency")
            fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/E2_topics_over_time.png"); plt.close()
        except Exception:
            pass

    # ============================================================ print
    pd.set_option("display.width", 220, "display.max_colwidth", 60)
    print("\n==================== CLUSTER x THEME CROSSWALK ====================")
    print(cw.to_string(index=False))
    print(f"\nOutlier rate {outlier_rate:.1%}; coverage {coverage:.0%}; novel topics {len(novel)}.")
    verdict = ("CORROBORATES taxonomy (ship as appendix)" if len(novel) == 0
               else f"finds {len(novel)} candidate novel theme(s) — verify exemplars")
    print("VERDICT:", verdict)
    print("\nDONE — wrote CC2_cluster_theme_crosswalk/novel_topics_exemplars/topics_over_time + charts E1-E3.")


if __name__ == "__main__":
    main()
