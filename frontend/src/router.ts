import { createRouter, createWebHistory } from "vue-router";

import PlayerView from "./views/PlayerView.vue";
import SongAdminView from "./views/SongAdminView.vue";
import SongListView from "./views/SongListView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: "/songs",
    },
    {
      path: "/songs",
      name: "songs",
      component: SongListView,
    },
    {
      path: "/songs/:id/admin",
      name: "song-admin",
      component: SongAdminView,
      props: true,
    },
    {
      path: "/songs/:id/player",
      name: "song-player",
      component: PlayerView,
      props: true,
    },
  ],
});
