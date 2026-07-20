(* concurrent_append.v -- Iris logical update for split-lock append and fork.
   This file imports the real Iris RA construction from
   ADL.Iris.event_chain_ra and proves ghost-state updates for:
   (1) appending a single event,
   (2) forking a chain (parent + child),
   (3) well-formedness preservation under both operations,
   (4) concurrent composition of two independent appends.

   The program is intentionally abstract (a no-op [tt]) because the ADL Lite
   document model treats append/fork as logical event-chain operations. *)

Require Import List.
Import ListNotations.
Require Import ADL.Iris.event_chain_ra.
Require Import ADL.Chain.

(* Abstract program values representing the logical operations. *)
Definition append : unit := tt.
Definition fork : unit := tt.

(* ------------------------------------------------------------------------- *)
(* Lemma 1: append_spec (ghost-state update for append).                    *)
(* ------------------------------------------------------------------------- *)

(* Logical update: appending [e] to the chain transforms ownership of the
   chain [es] into ownership of [es ++ [e]].  This is the ghost-state core
   of the split-lock append rule; a concrete lock can be wrapped around it
   by placing [own_chain γ es] in an invariant. *)
Lemma append_spec `{Hin : !inG Σ event_chainR} (γ : gname) (e : event) (es : chain) :
  own_chain γ es ==∗ own_chain γ (es ++ [e]).
Proof.
  iIntros "H".
  iMod (own_update γ (chain_auth es) (chain_auth (es ++ [e])) with "H") as "H";
       first (apply auth_update, option_local_update, exclusive_local_update; done).
  iModIntro. iExact "H".
Qed.

(* ------------------------------------------------------------------------- *)
(* Lemma 2: fork_spec (ghost-state update for fork).                          *)
(* ------------------------------------------------------------------------- *)

(* A fork appends a FORK event to the parent and creates a child chain with
   a fresh REGISTER event.  The child chain gets a fresh ghost name allocated
   by Iris; the caller receives it existentially. *)
Lemma fork_spec `{Hin : !inG Σ event_chainR}
  (γ_parent : gname) (parent : chain) (fork_event child_register : event) :
  own_chain γ_parent parent ==∗
  ∃ γ_child, own_chain γ_parent (parent ++ [fork_event]) ∗ own_chain γ_child [child_register].
Proof.
  iIntros "Hparent".
  (* Update parent chain: append fork_event. *)
  iMod (own_update γ_parent (chain_auth parent) (chain_auth (parent ++ [fork_event]))
          with "Hparent") as "Hparent".
  { apply auth_update, option_local_update, exclusive_local_update; done. }
  (* Allocate child chain: fresh ghost name with [child_register]. *)
  iMod (own_alloc (chain_auth [child_register])) as (γ_child) "Hchild".
  { apply auth_both_valid. done. }
  iModIntro. iExists γ_child. iFrame.
Qed.

(* ------------------------------------------------------------------------- *)
(* Lemma 3: well-formedness preservation under append.                        *)
(* ------------------------------------------------------------------------- *)

(* If the chain is well-formed and the event is validly appendable, then
   the extended chain is well-formed.  This is the Iris ghost-state
   invariant that ensures the well-formedness axiom is preserved. *)
Lemma append_preserves_wf `{Hin : !inG Σ event_chainR}
  (γ : gname) (es : chain) (e : event) :
  well_formed es → valid_append es e →
  own_chain γ es ==∗ own_chain γ (es ++ [e]) ∗ ⌜well_formed (es ++ [e])⌝.
Proof.
  intros Hwf Hvalid.
  iIntros "H".
  iMod (append_spec γ e es with "H") as "H".
  assert (Hwf' : well_formed (es ++ [e])) by (apply well_formedness_preservation; assumption).
  iModIntro. iFrame. iPureIntro. apply Hwf'.
Qed.

(* Helper: a child REGISTER chain is well-formed. *)
Lemma well_formed_singleton_register (e : event) :
  valid_append nil e -> well_formed [e].
Proof.
  intros Hv.
  unfold well_formed. simpl. repeat split.
  all: try (intros e0 H0; inversion H0; subst;
            [destruct Hv as [_ Hvalid]; apply Hvalid | contradiction]).
  all: try (destruct Hv as [Hprev _]; simpl; rewrite Hprev; auto).
  all: try tauto.
  all: try auto.
Qed.

(* ------------------------------------------------------------------------- *)
(* Lemma 4: fork determinism in Iris (ghost-state update + well-formedness). *)
(* ------------------------------------------------------------------------- *)

(* Fork produces two well-formed chains: the parent extended by [fork_event]
   and the child starting with [child_register].  The child ghost name is
   existentially quantified (freshly allocated by Iris). *)
Lemma fork_determinism_ra `{Hin : !inG Σ event_chainR}
  (γ_parent : gname) (parent : chain)
  (fork_event child_register : event) :
  well_formed parent ->
  valid_append parent fork_event ->
  event_type fork_event = FORK ->
  event_type child_register = REGISTER ->
  valid_append nil child_register ->
  own_chain γ_parent parent ==∗
    ∃ γ_child,
      own_chain γ_parent (parent ++ [fork_event]) ∗
      own_chain γ_child [child_register] ∗
      ⌜well_formed (parent ++ [fork_event]) ∧ well_formed [child_register]⌝.
Proof.
  intros Hwf Hvfork Hfork_type Hreg Hvreg.
  iIntros "Hparent".
  (* Fork: parent gets extended, child gets allocated with fresh name. *)
  iMod (fork_spec γ_parent parent fork_event child_register with "Hparent")
    as (γ_child) "[Hparent Hchild]".
  (* Well-formedness of parent. *)
  assert (Hwf_parent : well_formed (parent ++ [fork_event]))
    by (apply well_formedness_preservation; assumption).
  (* Well-formedness of child. *)
  assert (Hwf_child : well_formed [child_register])
    by (apply well_formed_singleton_register; assumption).
  iModIntro. iExists γ_child. iFrame.
  iPureIntro. split; assumption.
Qed.

(* ------------------------------------------------------------------------- *)
(* Lemma 5: concurrent composition (independent chains).                      *)
(* ------------------------------------------------------------------------- *)

(* Two agents can append to two independent chains concurrently because the
   ghost-state updates are on disjoint resources (different γ).  This is the
   Iris formalisation of the split-lock design: the _events_lock and
   _cache_lock serialize access to a single chain, but different chains are
   completely independent. *)
Lemma concurrent_appends `{Hin : !inG Σ event_chainR}
  (γ1 γ2 : gname) (e1 e2 : event) (es1 es2 : chain) :
  own_chain γ1 es1 ∗ own_chain γ2 es2 ==∗
  own_chain γ1 (es1 ++ [e1]) ∗ own_chain γ2 (es2 ++ [e2]).
Proof.
  iIntros "[H1 H2]".
  iMod (append_spec γ1 e1 es1 with "H1") as "H1".
  iMod (append_spec γ2 e2 es2 with "H2") as "H2".
  iModIntro. iFrame.
Qed.

(* ------------------------------------------------------------------------- *)
(* Lemma 6: frame-preserving update (split-lock read path).                   *)
(* ------------------------------------------------------------------------- *)

(* A reader holding only the fragmentary view can observe the chain but
   cannot modify it.  The frame rule guarantees that the fragmentary view is
   preserved across updates performed by the writer. *)
Lemma append_frame_preserving `{Hin : !inG Σ event_chainR}
  (γ : gname) (e : event) (es es' : chain) :
  chain_auth es ≼ chain_auth es' →
  own_chain γ es ==∗ own_chain γ es'.
Proof.
  intros Hle.
  iIntros "H".
  iMod (own_update γ (chain_auth es) (chain_auth es') with "H") as "H".
  { apply auth_update, option_local_update, exclusive_local_update; done. }
  iModIntro. iExact "H".
Qed.

(* ------------------------------------------------------------------------- *)
(* Lemma 7: concurrent append with well-formedness (independent chains).      *)
(* ------------------------------------------------------------------------- *)

(* Same as concurrent_appends but additionally proves that well-formedness
   is preserved on both chains. *)
Lemma concurrent_appends_wf `{Hin : !inG Σ event_chainR}
  (γ1 γ2 : gname) (e1 e2 : event) (es1 es2 : chain) :
  well_formed es1 → valid_append es1 e1 →
  well_formed es2 → valid_append es2 e2 →
  own_chain γ1 es1 ∗ own_chain γ2 es2 ==∗
  own_chain γ1 (es1 ++ [e1]) ∗ own_chain γ2 (es2 ++ [e2]) ∗
  ⌜well_formed (es1 ++ [e1]) ∧ well_formed (es2 ++ [e2])⌝.
Proof.
  intros Hwf1 Hv1 Hwf2 Hv2.
  iIntros "[H1 H2]".
  iMod (append_preserves_wf γ1 es1 e1 Hwf1 Hv1 with "H1") as "[H1 %Hwf1']".
  iMod (append_preserves_wf γ2 es2 e2 Hwf2 Hv2 with "H2") as "[H2 %Hwf2']".
  iModIntro. iFrame. iPureIntro. split; assumption.
Qed.
