// Universe OS: knoppen "Andere gebruiker" en "Afmelden" op het vergrendelscherm (gtklock 4-module).
// Gebaseerd op het patroon van gtklock-powerbar-module (Jovan Lanik, GPL-3+); gtklock-module.h is MIT.
// Afmelden vraagt een tweede klik binnen 5 s: niet-opgeslagen werk gaat verloren.
#include "gtklock-module.h"

#define DATA(x) ((struct knoppen *)(x)->module_data[self_id])

struct knoppen {
	GtkWidget *revealer, *wissel, *afmelden;
	guint terug;
};

const gchar module_name[] = "universe-knoppen";
const guint module_major_version = 4;
const guint module_minor_version = 0;

static int self_id;
static gchar *wissel_cmd = "/usr/bin/universe-wissel";
static gchar *afmeld_cmd = "/usr/lib/universe-os/universe-afmelden-vergrendeld";

GOptionEntry module_entries[] = {
	{ "wissel-command", 0, 0, G_OPTION_ARG_STRING, &wissel_cmd, NULL, NULL },
	{ "afmeld-command", 0, 0, G_OPTION_ARG_STRING, &afmeld_cmd, NULL, NULL },
	{ NULL },
};

static gboolean weer_aan(gpointer w) { gtk_widget_set_sensitive(GTK_WIDGET(w), TRUE); return G_SOURCE_REMOVE; }

static void wissel_klik(GtkButton *b, gpointer u) {
	gtk_widget_set_sensitive(GTK_WIDGET(b), FALSE);
	g_timeout_add(1500, weer_aan, b);
	g_spawn_command_line_async(wissel_cmd, NULL);
}

static gboolean afmeld_terug(gpointer u) {
	struct knoppen *k = u;
	k->terug = 0;
	gtk_button_set_label(GTK_BUTTON(k->afmelden), "Afmelden");
	return G_SOURCE_REMOVE;
}

static void afmeld_klik(GtkButton *b, gpointer u) {
	struct knoppen *k = u;
	if(!k->terug) {
		gtk_button_set_label(b, "Nogmaals klikken: afmelden (niet-opgeslagen werk gaat verloren)");
		k->terug = g_timeout_add_seconds(5, afmeld_terug, k);
		return;
	}
	g_source_remove(k->terug);
	k->terug = 0;
	gtk_widget_set_sensitive(GTK_WIDGET(b), FALSE);
	g_spawn_command_line_async(afmeld_cmd, NULL);
}

static void opruimen(struct Window *ctx) {
	struct knoppen *k = DATA(ctx);
	if(!k) return;
	if(k->terug) g_source_remove(k->terug);
	gtk_widget_destroy(k->revealer);
	g_free(k);
	ctx->module_data[self_id] = NULL;
}

static void maak(struct Window *ctx) {
	opruimen(ctx);
	struct knoppen *k = g_malloc0(sizeof *k);
	ctx->module_data[self_id] = k;
	k->revealer = gtk_revealer_new();
	g_object_set(k->revealer, "margin", 24, NULL);
	gtk_widget_set_halign(k->revealer, GTK_ALIGN_CENTER);
	gtk_widget_set_valign(k->revealer, GTK_ALIGN_END);
	gtk_widget_set_name(k->revealer, "universe-knoppen");
	gtk_revealer_set_transition_type(GTK_REVEALER(k->revealer), GTK_REVEALER_TRANSITION_TYPE_NONE);
	gtk_revealer_set_reveal_child(GTK_REVEALER(k->revealer), TRUE);
	gtk_overlay_add_overlay(GTK_OVERLAY(ctx->overlay), k->revealer);
	GtkWidget *box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 10);
	gtk_container_add(GTK_CONTAINER(k->revealer), box);
	k->wissel = gtk_button_new_with_label("Andere gebruiker");
	gtk_widget_set_name(k->wissel, "wissel-knop");
	g_signal_connect(k->wissel, "clicked", G_CALLBACK(wissel_klik), NULL);
	k->afmelden = gtk_button_new_with_label("Afmelden");
	gtk_widget_set_name(k->afmelden, "afmeld-knop");
	g_signal_connect(k->afmelden, "clicked", G_CALLBACK(afmeld_klik), k);
	gtk_container_add(GTK_CONTAINER(box), k->wissel);
	gtk_container_add(GTK_CONTAINER(box), k->afmelden);
	gtk_widget_show_all(k->revealer);
}

void on_activation(struct GtkLock *gtklock, int id) { self_id = id; }

void on_focus_change(struct GtkLock *gtklock, struct Window *win, struct Window *old) {
	maak(win);
	if(gtklock->hidden) gtk_revealer_set_reveal_child(GTK_REVEALER(DATA(win)->revealer), FALSE);
	if(old && old != win && DATA(old)) gtk_revealer_set_reveal_child(GTK_REVEALER(DATA(old)->revealer), FALSE);
}

void on_window_destroy(struct GtkLock *gtklock, struct Window *ctx) { opruimen(ctx); }

void on_idle_hide(struct GtkLock *gtklock) {
	if(gtklock->focused_window && DATA(gtklock->focused_window))
		gtk_revealer_set_reveal_child(GTK_REVEALER(DATA(gtklock->focused_window)->revealer), FALSE);
}

void on_idle_show(struct GtkLock *gtklock) {
	if(gtklock->focused_window && DATA(gtklock->focused_window))
		gtk_revealer_set_reveal_child(GTK_REVEALER(DATA(gtklock->focused_window)->revealer), TRUE);
}
