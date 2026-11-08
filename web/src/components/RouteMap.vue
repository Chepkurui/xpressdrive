<script setup>
// Stylised East African road network: the Northern Corridor from Mombasa to
// Kampala and on to Goma, Kigali and Juba, plus Tanzania via the Central
// Corridor (Kampala–Mwanza–Dodoma–Dar es Salaam) and the coast road from
// Mombasa through Tanga. Positions follow real geography
// (x = longitude, y = latitude), simplified. Return trucks run the other way.
</script>

<template>
  <div class="route" role="img" aria-label="Road network from Mombasa through Nairobi and the Malaba border to Kampala, then on to Goma in DR Congo, Kigali in Rwanda and Juba in South Sudan. In Tanzania, the Central Corridor runs from Kampala through the Mutukula border, Mwanza and Dodoma to Dar es Salaam, and a coast road links Mombasa to Dar es Salaam through Tanga. Trucks run both ways, including return trips to base.">
    <svg viewBox="0 0 900 500" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <defs>
        <path id="northern" d="M 838 344 L 624 244 L 508 180 L 434 175 L 306 185" />
        <path id="northern-back" d="M 306 185 L 434 175 L 508 180 L 624 244 L 838 344" />
        <path id="west" d="M 306 185 L 161 200 L 112 243 L 54 258" />
        <path id="rwanda" d="M 112 243 L 117 268" />
        <path id="north" d="M 306 185 L 285 98 L 231 23" />
        <path id="central" d="M 306 185 L 219 234 L 330 289 L 543 421 L 809 444" />
        <path id="coast" d="M 838 344 L 803 365 L 795 381 L 809 444" />
      </defs>

      <use href="#northern" class="lane" />
      <use href="#west" class="lane" />
      <use href="#rwanda" class="lane" />
      <use href="#north" class="lane" />
      <use href="#central" class="lane" />
      <use href="#coast" class="lane" />
      <use href="#northern" class="flow" />
      <use href="#west" class="flow" />
      <use href="#north" class="flow" />
      <use href="#rwanda" class="flow" />
      <use href="#central" class="flow" />
      <use href="#coast" class="flow" />

      <!-- Border posts -->
      <g class="border"><rect x="428" y="169" width="12" height="12" rx="2" /><text x="434" y="160" text-anchor="middle">Malaba</text></g>
      <g class="border"><rect x="76" y="246" width="10" height="10" rx="2" /></g>
      <g class="border"><rect x="252" y="55" width="10" height="10" rx="2" /></g>
      <g class="border"><rect x="214" y="229" width="10" height="10" rx="2" /></g>
      <g class="border"><rect x="798" y="360" width="10" height="10" rx="2" /></g>

      <!-- Cities -->
      <g class="place">
        <circle cx="838" cy="344" r="9" class="pulse" /><circle cx="838" cy="344" r="7" />
        <text x="822" y="338" text-anchor="end">Mombasa</text>
      </g>
      <g class="place"><circle cx="624" cy="244" r="6" /><text x="640" y="250">Nairobi</text></g>
      <g class="place"><circle cx="508" cy="180" r="4" class="hub" /><text x="512" y="206" class="sub">Eldoret</text></g>
      <g class="place">
        <circle cx="306" cy="185" r="9" class="pulse" style="animation-delay: 0.8s" /><circle cx="306" cy="185" r="7" />
        <text x="322" y="214">Kampala</text>
      </g>
      <g class="place"><circle cx="54" cy="258" r="6" /><text x="44" y="292" text-anchor="start">Goma</text><text x="44" y="310" class="sub">DR Congo</text></g>
      <g class="place"><circle cx="117" cy="268" r="6" /><text x="132" y="290">Kigali</text></g>
      <g class="place">
        <circle cx="231" cy="23" r="9" class="pulse" style="animation-delay: 1.6s" /><circle cx="231" cy="23" r="7" />
        <text x="250" y="28">Juba</text><text x="250" y="46" class="sub">South Sudan</text>
      </g>

      <g class="place"><circle cx="330" cy="289" r="6" /><text x="346" y="294">Mwanza</text></g>
      <g class="place"><circle cx="543" cy="421" r="4" class="hub" /><text x="543" y="446" text-anchor="middle" class="sub">Dodoma</text></g>
      <g class="place"><circle cx="795" cy="381" r="4" class="hub" /><text x="809" y="386" class="sub">Tanga</text></g>
      <g class="place">
        <circle cx="809" cy="444" r="9" class="pulse" style="animation-delay: 1.2s" /><circle cx="809" cy="444" r="7" />
        <text x="793" y="472" text-anchor="end">Dar es Salaam</text><text x="793" y="490" text-anchor="end" class="sub">Tanzania</text>
      </g>

      <!-- Trucks -->
      <g class="mover">
        <text class="emoji" text-anchor="middle" dominant-baseline="central">🚚</text>
        <animateMotion dur="12s" repeatCount="indefinite" calcMode="linear"><mpath href="#northern" /></animateMotion>
      </g>
      <g class="mover">
        <text class="emoji" text-anchor="middle" dominant-baseline="central">🚛</text>
        <animateMotion dur="12s" begin="-5s" repeatCount="indefinite" calcMode="linear"><mpath href="#northern-back" /></animateMotion>
      </g>
      <g class="mover">
        <text class="emoji small" text-anchor="middle" dominant-baseline="central">🚚</text>
        <animateMotion dur="8s" repeatCount="indefinite" calcMode="linear"><mpath href="#west" /></animateMotion>
      </g>
      <g class="mover">
        <text class="emoji small" text-anchor="middle" dominant-baseline="central">🚚</text>
        <animateMotion dur="7s" begin="-2s" repeatCount="indefinite" calcMode="linear"><mpath href="#north" /></animateMotion>
      </g>

      <g class="mover">
        <text class="emoji small" text-anchor="middle" dominant-baseline="central">🚛</text>
        <animateMotion dur="14s" begin="-4s" repeatCount="indefinite" calcMode="linear"><mpath href="#central" /></animateMotion>
      </g>
      <g class="mover">
        <text class="emoji small" text-anchor="middle" dominant-baseline="central">🚚</text>
        <animateMotion dur="6s" begin="-1s" repeatCount="indefinite" calcMode="linear"><mpath href="#coast" /></animateMotion>
      </g>

      <text x="430" y="400" text-anchor="middle" class="tag">Central Corridor</text>
      <text x="700" y="320" text-anchor="middle" class="tag">Northern Corridor</text>
      <text x="560" y="140" text-anchor="middle" class="tag">Return trucks fill up too</text>
    </svg>
  </div>
</template>

<style scoped>
.route { width: 100%; max-width: 900px; margin: 0 auto; }
svg { width: 100%; height: auto; overflow: visible; display: block; }
.lane { fill: none; stroke: rgba(255, 255, 255, 0.22); stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; }
.flow { fill: none; stroke: var(--amber); stroke-width: 2; stroke-dasharray: 8 12; animation: flow 1.4s linear infinite; }
.place circle { fill: var(--amber); }
.place .hub { fill: #ffd2a6; }
.border rect { fill: #fff; opacity: 0.9; }
.border text { fill: #d2deea; font-size: 12px; font-weight: 600; }
.pulse { fill: var(--amber); opacity: 0.6; transform-box: fill-box; transform-origin: center; animation: pulse 2.4s ease-out infinite; }
text { fill: #fff; font-size: 17px; font-weight: 700; font-family: inherit; }
text.sub { fill: #a9bdd1; font-size: 13px; font-weight: 500; }
text.tag { fill: #d2deea; font-size: 14px; font-weight: 600; letter-spacing: 0.04em; }
.emoji { font-size: 24px; }
.emoji.small { font-size: 18px; }
@keyframes flow { to { stroke-dashoffset: -20; } }
@keyframes pulse { from { transform: scale(1); opacity: 0.6; } to { transform: scale(3.2); opacity: 0; } }
@media (prefers-reduced-motion: reduce) {
  .flow, .pulse { animation: none; }
  .mover { display: none; }
}
</style>
