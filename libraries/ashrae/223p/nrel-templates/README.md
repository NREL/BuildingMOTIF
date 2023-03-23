# NREL 223P Templates

This is a collection of 223P templates we have found helpful to development of 223P models. These rely on a small number of adjustments to the 223P ontology which we are planning on upstreaming soon:

- [ ] `s223:HeatExchanger-Cooling/Heating` not defined? (what are the right roles?)
- [ ] `s223:Role-HeatExchanger` not defined but mentioned under `s223:HeatExchanger`
- [ ] add Flow Status from G36?
- [ ] inverse relations dont' seem to be added (`connectsThrough` -> `connectsAt`)
- [ ] how is `s223:MeasuredPropertyRule` supposed to work? It seems to fire unnecessarily and add blank node properties everywhere -- does it need a condition?
- [ ] missing FCU in 223P
