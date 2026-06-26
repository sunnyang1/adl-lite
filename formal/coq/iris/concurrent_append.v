(* concurrent_append.v -- Iris logical update for a split-lock append.
   This file imports the real Iris RA construction from
   ADL.Iris.event_chain_ra and proves a ghost-state update for appending an
   event to the chain.  The actual program is intentionally left abstract
   (a no-op [tt]) because the ADL Lite document model treats append as a
   logical event-chain operation. *)

Require Import List.
Import ListNotations.
Require Import ADL.Iris.event_chain_ra.

(* Abstract program value representing the append operation. *)
Definition append : unit := tt.

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
