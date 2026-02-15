# Album Form-by-Form Input with Song Reference

## Overview

MuseWave now provides an intuitive form-by-form album creation experience where users can input each song's details sequentially with the ability to quickly reference or copy settings from previously entered songs.

---

## How It Works

### 1. **Mode Selection**
Start by selecting "Album" mode when creating music. This enables the album workflow.

```
┌─────────────────────────────────────────┐
│  Single Song  │  Album (Create Multi)   │
└─────────────────────────────────────────┘
```

### 2. **Set Number of Tracks**
Specify how many tracks you want in your album (2-8 tracks).

```
Number of Tracks: [3] tracks with cohesive variation
```

### 3. **Track List Overview**
You'll see a collapsible list of all tracks in your album. Each shows:
- Track number and title (if filled)
- Brief description preview
- Collapse/expand chevron

```
Track 1: Midnight Dreams
  └─ Dreamy electronic soundscape with ambient vibes...

Track 2: (Not configured)
  └─ (No description yet)

Track 3: (Not configured)
  └─ (No description yet)
```

### 4. **Form-by-Form Configuration**
Click on any track to expand it and fill in its details:

#### **4.1 Quick Copy from Previous Track**
At the top of each expanded form (for tracks 2+), you'll see quick copy options:

```
┌────────────────────────────────────────────────────────┐
│ QUICK COPY FROM PREVIOUS TRACK                         │
├────────────────────────────────────────────────────────┤
│ [Copy All from Track 2] [Copy Style & Genres]         │
│ [Copy Genres Only] [Copy Languages]                   │
└────────────────────────────────────────────────────────┘
```

##### **Copy Options Explained:**

| Option | What It Copies | Use Case |
|--------|---|---|
| **Copy All from Track X** | Title (with "Variation" suffix), Description, Genres, Duration, Languages, Lyrics, Artist Inspiration, Video Style | Starting a track very similar to the previous one |
| **Copy Style & Genres** | Description, Genres, Languages | Keeping similar vibe but changing other details |
| **Copy Genres Only** | Just the musical genres | Maintaining album cohesion with genre consistency |
| **Copy Languages** | Just vocal languages | Same vocal style across different instrumental styles |

#### **4.2 Form Fields**
After copying (or starting fresh), fill in:

- **Track Title**: Name of the song
- **Track Description**: Mood, style, instrumentation details
- **Duration**: Length in seconds or MM:SS format
- **Lyrics/Concept**: Lyrical themes or vocal concepts
- **Genres**: Musical genres (multi-select)
- **Vocal Languages**: Languages for vocals (multi-select)

Each field has:
- **AI Suggest Button** (✨): Auto-generate suggestions
- **Previous Value Reference**: If copied, shows the source

#### **4.3 Reference Indicator**
If you copy from a previous track, you'll see a reference badge:

```
Track 2 Details
┌─────────────────────────────────────────┐
│ Referenced from Track 1                 │
└─────────────────────────────────────────┘
```

### 5. **Form Navigation**
- **Click "Done Configuring Track X"** to collapse and move to the next track
- **Click track header again** to re-open and edit
- All data is auto-saved as you type

### 6. **Submit All Tracks**
Once all tracks are configured:
1. Set album name (at the bottom)
2. Set album description and global settings
3. Click "Create Album"
4. All tracks are generated with their individual configurations

---

## Feature Details

### **Copy Mechanism**

When you click "Copy All from Track 2" while configuring Track 3:

**Before:**
```
Track 2 (Source):
  Title: "Midnight Dreams"
  Genres: [Electronic, Ambient]
  Duration: 120s

Track 3 (Destination - Empty):
  Title: ""
  Genres: []
  Duration: 25s (default)
```

**After:**
```
Track 2 (Source - Unchanged):
  Title: "Midnight Dreams"
  Genres: [Electronic, Ambient]
  Duration: 120s

Track 3 (Updated):
  Title: "Midnight Dreams (Variation)"
  Genres: [Electronic, Ambient]
  Duration: 120s
  ✓ Referenced from Track 2
```

### **Smart Variations**

The system intelligently handles copies:
- **Title Modification**: Adds "(Variation)" suffix to avoid duplication
- **List Copying**: Arrays (genres, languages) are deep-copied to prevent linked updates
- **Duration Preservation**: Exact duration values copied for consistency
- **Metadata Preservation**: All metadata fields transferred correctly

### **Reference Tracking**

Each track remembers which track it was copied from:
```javascript
{
  songIndex: 2,          // Track 3
  referencedFrom: 1,     // Copied from Track 2
  type: "all"            // What was copied (all, style, genres, languages)
}
```

---

## Workflow Examples

### **Example 1: Album with Similar Vibes**

```
Track 1 - "Midnight Dreams" (Electronic Ambient)
  └─ Click Track 1, fill all details

Track 2 - "Urban Echoes" (Same vibe, different mood)
  └─ Expand Track 2
  └─ Click "Copy Style & Genres" from Track 1
  └─ Modify title and description for different mood
  └─ Keep same genres and languages
  └─ Adjust duration as needed

Track 3 - "Digital Sunrise" (Similar theme)
  └─ Expand Track 3
  └─ Click "Copy All from Track 2"
  └─ System auto-fills all fields
  └─ Fine-tune title, lyrics, and duration
  └─ Ready to create!
```

**Result**: Cohesive album with 3 electronic-ambient tracks with variations.

---

### **Example 2: Album with Genre Progression**

```
Track 1 - "Soft Intro" (Ambient Jazz)
  └─ Fill details manually

Track 2 - "Building Energy" (Funk + Electronic)
  └─ Copy "Copy Genres Only" from Track 1 (gets Jazz)
  └─ Override with Funk, Electronic
  └─ Keep language as English
  └─ Modify duration and description

Track 3 - "Peak Energy" (Funk + Rock)
  └─ Copy "Copy Languages" from Track 2 (gets English)
  └─ Manually set Funk, Rock genres
  └─ Adjust tempo and intensity
```

**Result**: Genre-varied album with consistent vocal language.

---

## Best Practices

### ✅ **Do's**
- **Use "Copy All"** when starting with a very similar track
- **Use "Copy Style"** to maintain cohesion while varying content
- **Use "Copy Genres"** for genre-consistent albums
- **Modify titles** even after copying to reflect track uniqueness
- **Review all fields** after copying to ensure correctness
- **Mix copying strategies** across your album for variety

### ❌ **Don'ts**
- Don't copy all fields if you want drastically different tracks
- Don't leave generic titles (the "(Variation)" suffix is just a starting point)
- Don't copy genres blindly if pursuing genre-mixed albums
- Don't forget to update lyrics/concepts for each track
- Don't submit without reviewing copied fields

---

## Technical Details

### **State Management**

The feature uses React hooks for state:

```javascript
// Track which song was referenced
const [songReference, setSongReference] = useState(null);

// Copy function
const copySongFromPrevious = (toIndex, fromIndex, copyType) => {
  // Copies specified fields from source track
  // Updates destination track
  // Sets reference badge
  // Shows success toast
}
```

### **Copy Types**

Four copy strategies implemented:

| Type | Fields | Code |
|------|--------|------|
| `"all"` | All fields except ID | Most comprehensive |
| `"style"` | musicPrompt, genres, languages | Vibe matching |
| `"genres"` | selectedGenres array | Genre consistency |
| `"languages"` | vocalLanguages array | Language uniformity |

### **Data Preservation**

All copied data is:
- **Deep-copied** (not referenced)
- **Validated** against genre/language lists
- **Type-safe** (matching source field types)
- **Reversible** (user can edit after copying)

---

## User Experience Features

### **Visual Feedback**

- **Toast notifications**: "Track 2 updated from Track 1"
- **Reference badge**: Shows source track clearly
- **Button states**: Disabled on single tracks (no previous to copy)
- **Animation**: Smooth expand/collapse of track sections

### **Accessibility**

- **Keyboard navigation**: Tab through all copy buttons
- **Semantic HTML**: Proper button and label elements
- **Color contrast**: WCAG AA compliant colors
- **Screen reader support**: Clear button labels

### **Mobile Responsive**

- Copy buttons wrap on small screens
- Expandable sections collapse properly
- Touch-friendly button sizing (min 44px height)
- Full-width forms on mobile

---

## Integration with Other Features

### **AI Suggestions**
Each field still has AI suggestion buttons (✨) after copying:
- Suggest new title based on description
- Suggest genres matching description
- AI suggestions work independently of copy

### **Form Validation**
- Copied values pass through same validation as manual input
- Invalid copied genres are filtered out
- Duration parsing works same way

### **Album Creation Endpoint**
Backend receives album with complete track specifications:
```json
{
  "album_title": "My Album",
  "songs": [
    {
      "title": "Track 1 Title",
      "musicPrompt": "Description...",
      "selectedGenres": ["Electronic"],
      ...
    },
    {
      "title": "Track 2 Title",
      "musicPrompt": "Different description...",
      "selectedGenres": ["Electronic"],
      ...
    }
  ]
}
```

---

## Future Enhancements

### 🔄 **Potential Features**
1. **Copy between any tracks** (not just previous)
   - Dropdown selector to choose source track
   - Enable pattern creation (Track 1, 3, 5 similar)

2. **Template-based creation**
   - "Save this track as template"
   - Apply template to multiple tracks
   - Share templates with other users

3. **Track ordering**
   - Drag-and-drop reorder tracks
   - Duplicate tracks within album
   - Smart gap placement

4. **Conditional copy**
   - "Copy if empty" (only copy if field blank)
   - Merge genres (combine instead of replace)
   - Progressive variation

5. **Copy history**
   - Undo/redo for album tracks
   - View what was copied
   - Restore original if needed

---

## Troubleshooting

### **Issue: "Copy All" didn't copy everything**
**Solution**: Check that all source fields were filled. Empty fields are preserved as empty in destination.

### **Issue: Genres changed after copying**
**Solution**: The system validates genres against available list. Invalid genres are filtered out. Use "Copy Genres Only" to verify what was copied.

### **Issue: Title still has "(Variation)" and I want to remove it**
**Solution**: Simply edit the title field after copying. The "(Variation)" is just a suggestion.

### **Issue: Reference badge not showing**
**Solution**: Reference badge only shows after successful copy. Close and re-open the track form to refresh.

---

## Summary

The form-by-form album creation with song reference feature streamlines creating cohesive multi-track albums by:

✅ Reducing repetitive data entry
✅ Maintaining album consistency
✅ Enabling quick variations
✅ Preserving creative control
✅ Providing smart copy strategies
✅ Maintaining full transparency (who copied from whom)

Create albums faster while maintaining quality and variation!
