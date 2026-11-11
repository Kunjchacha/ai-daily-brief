# AI Daily Brief: Research in plain English, Friday 13 November 2026 (Morning)
Status: DRAFT

- Rule checks (no AI judgement of the facts): summary checked against the abstract: the quote below is a word-for-word match; every number in the summary appears in the abstract; 71 upvotes on Hugging Face Daily Papers; labelled as the authors' own claims, not independently verified

HOW TO APPROVE
1. Read every item. Edit any wording below (keep the 'Field:' labels as they are).
2. Not a confirmed fact (a rumour, prediction, plan or opinion)? Change 'Include: yes' to 'Include: no'.
3. Replace any [ADD YOUR LINE] with your own line, and check each source link.
4. When you are happy, change 'Status: DRAFT' above to 'Status: APPROVED' and save.
5. Run Actions > Approve issue. Only then is the final post text produced.
OPTIONAL: on a 'Take:' line, add one sentence of your own experience or opinion. A real personal line is the best way to stop a post sounding generic.

## 1. Tree-Ising: Repairing Language Models with Bit-Level Ising Edits
Hook: A new AI paper is getting attention: Tree-Ising: Repairing Language Models with Bit-Level Ising Edits
Points: The authors introduce Tree-Ising, a method that casts repairing a language model’s BF16 weights as a sparse discrete optimization problem solved via independent QUBO (Ising) formulations on a GPU. They report that Tree-Ising improves math benchmark performance, achieving 54.6% on MATH-500 (and 55.1% with simulated bifurcation), modifies fewer weights, requires only four forward-pass requests, and costs about $0.90 in GPU time. || The authors report: "On the agent's two layers, Tree-Ising achieves 54.6% on MATH-500, outperforming the agent's edit (51.7%) under the same evaluation protocol, while the base model scores 7.9% as reported."
Takeaway: These are the authors' own claims, and a preprint may not have been peer reviewed yet.
Take: 
Ask: Does this match what you see in practice?
Source: arXiv | https://arxiv.org/abs/2611.14210
Evidence from the source: On the agent's two layers, Tree-Ising achieves 54.6% on MATH-500, outperforming the agent's edit (51.7%) under the same evaluation protocol, while the base model scores 7.9% as reported.
Kind: research
Age: 43 hours old
Include: yes
