# Validation multi-marques

Grille: faits25, audience/offre20, argument20, continuité15, finition10, absence de promesses indues/répétitions10. Jugement interne, pas une mesure de conversion.
Preset fast; Fathom ajoute une revue de séquence et une consigne propre à email2. Connaissances et audience existantes; aucune aide factuelle manuelle.

Séquence de 3 emails FR, revue de séquence activée, phrase finale imposée uniquement à email2; remplace le test Fathom périmé.

Itération 1: échec partiel, 1/3 emails. Cause vérifiée: overlap_gate traite la déclaration d'affiliation obligatoire comme argument répétitif. Hypothèse: retirer seulement les clauses de déclaration d'affiliation reconnues de la comparaison de variété, en gardant le reste du paragraphe, les objets et les contrôles factuels. Attendu: trois emails distincts avec mention transparente conservée dans chacun. Le snapshot initial reste immuable.

Rejeu: les3emails passent désormais la rédaction individuelle, mais la revue de séquence appelle overlap_gate sans identité de marque; elle signale encore la même déclaration. Correction de propagation nécessaire dans SequenceReviewer et pipeline, test sur le contrôle de séquence lui-même. Ne pas attribuer cette reprise supplémentaire à un défaut commercial du texte.

Itération2:76/100, première séquence complète donc delta non applicable; meilleur76. Trois axes distincts et preuves conservées; bénéfice opérationnel sous-exploité. Faux positif affiliation corrigé dans les deux chemins, contrôle déterministe des vrais textes vide. Retouche email2:125→91mots,1appel, phrase dédiée conservée. Verdict: relecture éditoriale nécessaire; aucune conversion mesurée.
