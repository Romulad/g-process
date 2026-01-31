# Gunicorn Internals

How does gunicorn work under the hood?

This repository documents how **Gunicorn works internally**, from running  `gunicorn app:app` all the way to request handling, 
with **direct references to the source code**.

Gunicorn is downloaded **millions of times every month** and sits at the core of many production Python systems, yet its internal architecture is rarely explored in detail. This project aims to change that.

**Documented versions:** `23.0.0`

---

## Why this project exists

This work started from a simple curiosity:
how does [Uvicorn](https://github.com/Kludex/uvicorn) achieve such impressive performance?

We often hear that it’s “because of async” or “non-blocking I/O”, but *how exactly does that work in practice*?

While exploring Uvicorn’s codebase, I noticed that Gunicorn was part of the picture. At the time, this was intriguing to me — Gunicorn and Uvicorn… how and why? That led me to dig deeper into Gunicorn itself — starting from the entry point and following the execution flow step by step.

As I read the code, I began documenting what I was learning to:

* better understand the architecture,
* keep track of important design decisions,
* and make the codebase easier to reason about.

Although this documentation started as personal notes, I realized how helpful it would have been to have something like this when I first wanted to understand Gunicorn internals.
That’s how this project was born.

---

## Who this is for

This project is for developers who want to go **beyond using Gunicorn** and actually understand how it works.

In particular, it may be useful if you:

* use Gunicorn in production and want a clearer mental model of its internals,
* are curious about process models, worker management, and request handling,
* want to learn from a real-world, battle-tested codebase,
* enjoy reading source code and understanding *why* certain architectural decisions were made.

It is not a step-by-step tutorial, but rather a **guided walkthrough of the code**, focused on structure, flow, and design choices.

---

## Gunicorn versions

Gunicorn evolves over time. At the moment of writing:

* version **23.0.0** is stable and widely used,
* the **24.x** series is available, with ASGI support still in beta.

To keep things clear and accurate, documentation in this repository is **versioned**.
Each Gunicorn version has its own dedicated folder (for example: `v23.0.0/`).

Currently:

* `23.0.0` is the first documented version,
* more versions may be added over time.

---

## Support the project ⭐

If you find this documentation useful or learn something new from it, consider **starring the repository**.

It helps others discover the project and motivates me to continue:

* exploring more parts of Gunicorn,
* documenting newer versions,
* and improving clarity over time.

Thank you for reading — and happy code diving 🚀

---

## Getting started

* 📘 **[Gunicorn 23.0.0 internals](/v23.0.0/Readme.md)**

---

## Contributions

Contributions are very welcome 🙌

If you want to:

* add new explanations,
* correct or clarify existing ones,
* improve wording or structure,
* suggest missing topics,

feel free to fork the repository and open a pull request.

---

## License

See the `LICENSE` file in this repository for details.
