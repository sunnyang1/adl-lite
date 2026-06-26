(* event_chain_ra.v -- resource algebra for an authoritative event chain.
   This version uses Iris's auth( option(excl) ) camera to model the chain
   as a single ghost variable that can be updated when the caller owns both
   the authoritative and the fragmentary view. *)

From iris.algebra Require Export auth excl ofe.
From iris.base_logic.lib Require Export own.
From iris.proofmode Require Export proofmode.
Require Export ADL.Event ADL.Chain.

(* The chain is a discrete OFE with Leibniz equality. *)
Notation chainO := (leibnizO chain) (only parsing).

(* Authoritative-exclusive camera for the whole chain.
   The authoritative element represents the current chain;
   the fragmentary element lets clients observe (and, together with the auth,
   update) the chain. *)
Definition event_chainR : cmra := authR (optionUR (exclR chainO)).

(* The raw camera element that represents full ownership of a concrete chain
   [es].  Exposed here so that callers can invoke [own_update] explicitly. *)
Definition chain_auth (es : chain) : event_chainR :=
  ● (Some (Excl (es : chainO))) ⋅ ◯ (Some (Excl (es : chainO))).

(* Ownership of the full chain.  The ghost name [γ] identifies this particular
   chain. *)
Definition own_chain `{Hin : !inG Σ event_chainR} (γ : gname) (es : chain) : iProp Σ :=
  own γ (chain_auth es).
