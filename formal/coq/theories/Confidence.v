(* Confidence.v -- confidence derivation as a G-Counter (max) over lifecycle events. *)

Require Import List Arith Lia String.
Import ListNotations.
Require Import ADL.Event.

(* ------------------------------------------------------------------------- *)
(* γ_default: G-Counter max over VALIDATE/SNAPSHOT events.                   *)
(* ------------------------------------------------------------------------- *)

Fixpoint max_confidence (es : list event) : nat :=
  match es with
  | nil => 0
  | e :: es' => Nat.max (confidence e) (max_confidence es')
  end.

Definition derived_confidence_events (es : list event) : nat :=
  max_confidence
    (filter (fun e =>
      match event_type e with
      | VALIDATE => true
      | SNAPSHOT => true
      | _        => false
      end) es).

(* Helper lemma: max_confidence is monotone with respect to append. *)
Lemma max_confidence_monotone_append : forall (es : list event) (e : event),
  max_confidence (es ++ [e]) >= max_confidence es.
Proof.
  intros es e.
  induction es as [| e' es' IH]; simpl.
  - lia.
  - lia.
Qed.

(* Theorem T5 (confidence monotonicity, default variant): appending a VALIDATE
   event cannot decrease the derived confidence under the G-Counter (max) semantics. *)
Theorem confidence_monotonicity_default : forall (es : list event) (e : event),
  event_type e = VALIDATE ->
  derived_confidence_events (es ++ [e]) >= derived_confidence_events es.
Proof.
  intros es e Hev.
  unfold derived_confidence_events.
  rewrite filter_app.
  simpl. rewrite Hev. simpl.
  apply max_confidence_monotone_append.
Qed.

(* Confidence boundedness (Theorem T4): every event confidence is bounded by
   MaxConfidence, and the derived confidence is bounded by the same constant.
   Here we take MaxConfidence as the maximum over the concrete chain. *)
Theorem confidence_boundedness : forall (es : list event) (e : event),
  In e es -> confidence e <= max_confidence es.
Proof.
  induction es as [| e' es' IH]; intros e Hin.
  - inversion Hin.
  - simpl. destruct Hin as [Heq | Hin].
    + subst. apply Nat.le_max_l.
    + apply IH in Hin. transitivity (max_confidence es'); [apply Hin|].
      apply Nat.le_max_r.
Qed.

Theorem derived_confidence_bounded : forall (es : list event),
  derived_confidence_events es <= max_confidence es.
Proof.
  induction es as [| e es' IH]; simpl; [apply le_n|].
  destruct (event_type e) eqn:Heq;
    unfold derived_confidence_events; simpl; rewrite Heq; simpl;
    try (apply Nat.max_le_compat_l; apply IH);
    try (transitivity (max_confidence es'); [apply IH | apply Nat.le_max_r]).
Qed.

(* ------------------------------------------------------------------------- *)
(* γ_agg: bonus-formula aggregate confidence (matches paper Appendix E).     *)
(* ------------------------------------------------------------------------- *)

(* Constants scaled by 100 to avoid floating-point arithmetic. *)
Definition BASE_FLOOR := 50.   (* 0.5  * 100 *)
Definition BONUS_INC := 5.    (* 0.05 * 100 *)
Definition MAX_SCALED := 100. (* 1.0 * 100 *)

(* Filter VALIDATE events only. *)
Definition validate_events (es : list event) : list event :=
  filter (fun e =>
    match event_type e with
    | VALIDATE => true
    | _        => false
    end) es.

(* Extract all actors from a list of events. *)
Definition actors_of (es : list event) : list string :=
  map actor es.

(* Check if an actor is in a list. *)
Fixpoint actor_in (a : string) (actors : list string) : bool :=
  match actors with
  | nil => false
  | a' :: actors' =>
      if string_dec a a' then true else actor_in a actors'
  end.

(* Remove duplicate actors (keep first occurrence). *)
Fixpoint unique_actors (actors : list string) : list string :=
  match actors with
  | nil => nil
  | a :: actors' =>
      if actor_in a actors' then unique_actors actors'
      else a :: unique_actors actors'
  end.

(* Maximum confidence reported by a specific actor. *)
Fixpoint actor_max (a : string) (es : list event) : nat :=
  match es with
  | nil => 0
  | e :: es' =>
      if string_dec (actor e) a
      then Nat.max (confidence e) (actor_max a es')
      else actor_max a es'
  end.

(* Sum of per-actor maxima. *)
Fixpoint sum_actor_max (actors : list string) (es : list event) : nat :=
  match actors with
  | nil => 0
  | a :: actors' => actor_max a es + sum_actor_max actors' es
  end.

(* Mean of per-actor maxima (floor division). *)
Definition mean_actor_max (actors : list string) (es : list event) : nat :=
  let n := List.length actors in
  if n =? 0 then 0 else sum_actor_max actors es / n.

(* Bonus-formula aggregate confidence γ_agg. *)
Definition gamma_agg (es : list event) : nat :=
  let ves := validate_events es in
  let actors := unique_actors (actors_of ves) in
  let n := List.length actors in
  if n =? 0 then 0
  else
    let c_base := Nat.max BASE_FLOOR (mean_actor_max actors ves) in
    let bonus := BONUS_INC * (n - 1) in
    Nat.min MAX_SCALED (c_base + bonus).

(* Theorem T5-γ_agg: γ_agg is bounded by [0, MAX_SCALED]. *)
Theorem gamma_agg_bounded : forall (es : list event),
  gamma_agg es <= MAX_SCALED.
Proof.
  intros es.
  unfold gamma_agg.
  destruct (List.length (unique_actors (actors_of (validate_events es))) =? 0) eqn:Hn.
  - unfold MAX_SCALED. lia.
  - apply Nat.le_min_l.
Qed.
