#lang racket

(require racket/cmdline)
(require json)

;; This program converts a .json skp file into the easter egg language.

(define-values (input output err)
  (command-line #:args (input output err)
                (values input output err)))

(define (file->json path)
  (with-input-from-file path
    (lambda () (read-json))))

;; (display (hash-ref (file->json input) 'commands))


(define (skp->eegg commands)
  (for/list #;([accum '()])
            ([command commands])

    (define op (hash-ref command 'command))
    (match op
      ["DrawRect" "found drawrect"]
      [_ "don't know what this is"])
    )
  )

(define commands (hash-ref (file->json input) 'commands))

(display (skp->eegg commands))
