(* Status.v -- ADL Lite event lifecycle status lattice.
   Status is derived from EventChain, not stored as a mutable field.
   The lattice order is: PROVISIONAL < FORKED < VALIDATED < DEPRECATED < ARCHIVED. *)

Require Import List Arith Lia String.

Inductive status : Set :=
  | PROVISIONAL
  | FORKED
  | VALIDATED
  | DEPRECATED
  | ARCHIVED.

Definition status_rank (s : status) : nat :=
  match s with
  | PROVISIONAL => 0
  | FORKED      => 1
  | VALIDATED   => 2
  | DEPRECATED  => 3
  | ARCHIVED    => 4
  end.

Definition status_leq (s1 s2 : status) : Prop :=
  status_rank s1 <= status_rank s2.

Definition status_max (s1 s2 : status) : status :=
  if Nat.leb (status_rank s1) (status_rank s2) then s2 else s1.

Definition status_lub (ss : list status) : status :=
  match ss with
  | nil => PROVISIONAL
  | s :: ss' => fold_left status_max ss' s
  end.

Lemma status_leq_refl : forall s : status, status_leq s s.
Proof.
  intro s. unfold status_leq. apply le_n.
Qed.

Lemma status_leq_trans : forall s1 s2 s3 : status,
  status_leq s1 s2 -> status_leq s2 s3 -> status_leq s1 s3.
Proof.
  unfold status_leq. intros. lia.
Qed.

Lemma status_max_upper_bound : forall s1 s2 : status,
  status_leq s1 (status_max s1 s2) /\ status_leq s2 (status_max s1 s2).
Proof.
  intros s1 s2. unfold status_max, status_leq.
  destruct (Nat.leb (status_rank s1) (status_rank s2)) eqn:Heq.
  - rewrite Nat.leb_le in Heq. split; lia.
  - rewrite Nat.leb_gt in Heq. split; lia.
Qed.

Lemma status_max_least : forall s1 s2 b : status,
  status_leq s1 b -> status_leq s2 b -> status_leq (status_max s1 s2) b.
Proof.
  intros s1 s2 b H1 H2. unfold status_max, status_leq in *.
  destruct (Nat.leb (status_rank s1) (status_rank s2)) eqn:Heq.
  - rewrite Nat.leb_le in Heq. lia.
  - rewrite Nat.leb_gt in Heq. lia.
Qed.

Lemma status_max_monotone_r : forall s1 a b : status,
  status_leq a b -> status_leq (status_max s1 a) (status_max s1 b).
Proof.
  intros s1 a b Hab. unfold status_max, status_leq in *.
  destruct (Nat.leb (status_rank s1) (status_rank a)) eqn:Ha;
  destruct (Nat.leb (status_rank s1) (status_rank b)) eqn:Hb;
  try apply Nat.leb_le in Ha; try apply Nat.leb_gt in Ha;
  try apply Nat.leb_le in Hb; try apply Nat.leb_gt in Hb;
  simpl; lia.
Qed.

Lemma fold_left_status_max_acc_leq : forall (ss : list status) (acc : status),
  status_leq acc (fold_left status_max ss acc).
Proof.
  induction ss as [| s1 ss' IH]; simpl; intro acc.
  - apply status_leq_refl.
  - apply status_leq_trans with (status_max acc s1).
    + destruct (status_max_upper_bound acc s1) as [H _]; apply H.
    + apply IH.
Qed.


Lemma status_max_comm : forall a b : status, status_max a b = status_max b a.
Proof.
  intros a b. unfold status_max. destruct a; destruct b; reflexivity.
Qed.

Lemma status_max_monotone_l : forall a b s : status,
  status_leq a b -> status_leq (status_max a s) (status_max b s).
Proof.
  intros a b s Hab. rewrite status_max_comm. rewrite (status_max_comm b s).
  apply status_max_monotone_r. apply Hab.
Qed.

Lemma fold_left_status_max_monotone_acc : forall (ss : list status) (a b : status),
  status_leq a b -> status_leq (fold_left status_max ss a) (fold_left status_max ss b).
Proof.
  induction ss as [| s1 ss' IH]; simpl; intros x y Hxy.
  - apply Hxy.
  - apply (IH (status_max x s1) (status_max y s1) (status_max_monotone_l x y s1 Hxy)).
Qed.

Lemma status_lub_upper_bound : forall (ss : list status) (s : status),
  In s ss -> status_leq s (status_lub ss).
Proof.
  intros ss s Hin.
  destruct ss as [| s0 ss']; [inversion Hin|].
  simpl in Hin. destruct Hin as [Heq | Hin].
  - subst. apply fold_left_status_max_acc_leq.
  - induction ss' as [| s1 ss'' IH]; simpl in *.
    + inversion Hin.
    + destruct Hin as [Heq | Hin].
      * subst. apply status_leq_trans with (status_max s0 s).
        -- destruct (status_max_upper_bound s0 s) as [_ H]; apply H.
        -- apply fold_left_status_max_acc_leq.
      * apply status_leq_trans with (fold_left status_max ss'' s0).
        -- apply IH. apply Hin.
        -- apply fold_left_status_max_monotone_acc.
           destruct (status_max_upper_bound s0 s1) as [H _]; apply H.
Qed.

Lemma fold_left_status_max_least : forall (ss : list status) (acc b : status),
  status_leq acc b ->
  (forall s, In s ss -> status_leq s b) ->
  status_leq (fold_left status_max ss acc) b.
Proof.
  induction ss as [| s1 ss' IH]; simpl; intros acc b Hacc Hbound.
  - apply Hacc.
  - apply IH.
    + apply status_max_least; [apply Hacc | apply Hbound; left; reflexivity].
    + intros s Hin. apply Hbound. right. apply Hin.
Qed.

Lemma status_lub_least : forall (ss : list status) (b : status),
  (forall s : status, In s ss -> status_leq s b) -> status_leq (status_lub ss) b.
Proof.
  intros ss b Hbound.
  destruct ss as [| s0 ss']; simpl.
  - unfold status_leq. simpl. lia.
  - apply fold_left_status_max_least.
    + apply Hbound. left; reflexivity.
    + intros s Hin. apply Hbound. right. apply Hin.
Qed.

(* Theorem T3 (status monotonicity): the derived status of a chain is
   at least the derived status of any prefix.  We state the lemma here;
   the proof over chains appears in Invariants.v once Chain.v is available. *)
Theorem status_monotonic : forall (prefix suffix : list status),
  status_leq (status_lub prefix) (status_lub (prefix ++ suffix)).
Proof.
  intros prefix suffix.
  apply status_lub_least. intros s Hin.
  assert (In s (prefix ++ suffix)) by (apply in_or_app; left; apply Hin).
  apply status_lub_upper_bound. apply H.
Qed.
